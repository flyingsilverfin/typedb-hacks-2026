"""Query translator for converting natural language to TypeQL."""

import json
import os
from dataclasses import dataclass
from typing import Any

import anthropic

from .typedb_client import TypeDBClient


QUERY_TRANSLATION_PROMPT = """You are a TypeQL query generator for TypeDB 3.0. Convert natural language questions to TypeQL queries.

CURRENT SCHEMA:
{schema}

TYPEQL 3.0 SYNTAX REFERENCE:
- Match pattern: match $var isa type, has attr $a;
- Fetch results: fetch {{ "key": $var.* }};
- Relations: ($role: $var1, $role: $var2) isa relation_type
- Filter by value: has attr "value" or has attr $a; $a = "value";
- Subtype matching: $x isa! exact_type (exact) vs $x isa type (includes subtypes)

EXAMPLE QUERIES:

1. "What objects are in the room?"
match $obj isa physical_object;
fetch {{ "object": $obj.* }};

2. "What color is the chair?"
match $c isa chair, has color $color;
fetch {{ "chair": $c.name, "color": $color }};

3. "What is on the table?"
match
  $table isa table;
  $item isa physical_object;
  (subject: $item, reference: $table) isa on;
fetch {{ "item_on_table": $item.* }};

4. "Find all brown furniture"
match $f isa furniture, has color "brown";
fetch {{ "brown_furniture": $f.* }};

5. "What is next to the sofa?"
match
  $sofa isa physical_object, has name $n; $n contains "sofa";
  $other isa physical_object;
  (item: $sofa, item: $other) isa next_to;
fetch {{ "next_to_sofa": $other.* }};

QUESTION: {question}

Return ONLY the TypeQL query, no explanation or markdown. The query must be valid TypeQL 3.0 syntax."""


@dataclass
class QueryResult:
    """Result from query translation and execution."""
    question: str
    typeql: str
    results: list[dict[str, Any]]
    success: bool
    error: str | None = None


class QueryTranslator:
    """Translate natural language questions to TypeQL and execute them."""

    def __init__(
        self,
        client: TypeDBClient,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-20250514"
    ):
        """
        Initialize query translator.

        Args:
            client: TypeDB client for executing queries
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Claude model to use
        """
        self.client = client
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

        self.anthropic = anthropic.Anthropic(api_key=self.api_key)
        self.model = model

    def translate(self, question: str, schema: str | None = None) -> str:
        """
        Translate a natural language question to TypeQL.

        Args:
            question: Natural language question
            schema: Current schema (fetched automatically if not provided)

        Returns:
            TypeQL query string
        """
        if schema is None:
            schema = self._get_schema_for_prompt()

        prompt = QUERY_TRANSLATION_PROMPT.format(
            schema=schema,
            question=question
        )

        response = self.anthropic.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        typeql = response.content[0].text.strip()

        # Clean up any markdown formatting
        if typeql.startswith("```"):
            lines = typeql.split("\n")
            typeql = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

        return typeql

    def query(self, question: str) -> QueryResult:
        """
        Translate and execute a natural language query.

        Args:
            question: Natural language question

        Returns:
            QueryResult with TypeQL query and results
        """
        try:
            typeql = self.translate(question)

            results = self.client.execute_read(typeql)

            return QueryResult(
                question=question,
                typeql=typeql,
                results=results,
                success=True
            )

        except Exception as e:
            return QueryResult(
                question=question,
                typeql="",
                results=[],
                success=False,
                error=str(e)
            )

    def execute_typeql(self, typeql: str) -> QueryResult:
        """
        Execute a raw TypeQL query.

        Args:
            typeql: TypeQL query string

        Returns:
            QueryResult
        """
        try:
            results = self.client.execute_read(typeql)

            return QueryResult(
                question="(direct TypeQL)",
                typeql=typeql,
                results=results,
                success=True
            )

        except Exception as e:
            return QueryResult(
                question="(direct TypeQL)",
                typeql=typeql,
                results=[],
                success=False,
                error=str(e)
            )

    def _get_schema_for_prompt(self) -> str:
        """Get schema representation for the translation prompt."""
        schema = self.client.get_schema()
        if schema:
            return schema

        # Return minimal schema hint if we can't get the actual schema
        return """(Schema could not be retrieved. Assume standard types:
- physical_object with attributes: name, color, material, shape, size
- furniture sub physical_object
- Spatial relations: on, under, next_to, in_front_of, behind, inside, contains
- Relation roles: subject, reference)"""

    def format_results(self, result: QueryResult) -> str:
        """
        Format query results for display.

        Args:
            result: QueryResult to format

        Returns:
            Formatted string
        """
        lines = []

        lines.append(f"Question: {result.question}")
        lines.append(f"TypeQL: {result.typeql}")
        lines.append("")

        if not result.success:
            lines.append(f"Error: {result.error}")
            return "\n".join(lines)

        if not result.results:
            lines.append("No results found.")
            return "\n".join(lines)

        lines.append(f"Results ({len(result.results)}):")
        for i, doc in enumerate(result.results, 1):
            lines.append(f"  {i}. {json.dumps(doc, indent=4)}")

        return "\n".join(lines)
