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

CRITICAL SYNTAX RULES - TypeQL 3.0:
1. ALWAYS use variables starting with $ (e.g., $obj, $n, $color)
2. NEVER omit variables - every entity and attribute MUST have a variable
3. Match pattern: match $var isa type, has attr $a;
4. Fetch results: fetch {{ "key": $a }};  (fetch only attribute variables, NOT entity variables)
5. Relations: ($role: $var1, $role: $var2) isa relation_type
6. Subtype matching: $x isa! exact_type (exact) vs $x isa type (includes subtypes)

CORRECT EXAMPLES:

1. "What entities are in the scene?"
match $obj isa physical_object, has name $n;
fetch {{ "name": $n }};

2. "What color is the chair?"
match $c isa chair, has name $n, has color $color;
fetch {{ "name": $n, "color": $color }};

3. "What monitors are there?"
match $m isa monitor, has name $n;
fetch {{ "name": $n }};

4. "Find all black objects"
match $obj isa physical_object, has name $n, has color "black";
fetch {{ "name": $n }};

5. "What is the desk made of?"
match $d isa desk, has material $mat, has name $n;
fetch {{ "name": $n, "material": $mat }};

INVALID EXAMPLES (DO NOT USE):
- match isa physical_object;  ❌ Missing variable!
- match $obj isa physical_object; fetch {{ "entity": $obj }};  ❌ Cannot fetch entity variable!
- match $obj has name;  ❌ Missing variable for attribute!

QUESTION: {question}

Return ONLY the TypeQL query with correct variable usage, no explanation or markdown."""


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
        self.anthropic = None
        self.model = model

    def _ensure_anthropic_client(self):
        """Lazy initialization of Anthropic client for query translation."""
        if self.anthropic is None:
            if not self.api_key:
                raise ValueError(
                    "ANTHROPIC_API_KEY environment variable is required for natural language query translation.\n"
                    "Set it with: export ANTHROPIC_API_KEY=your_key_here\n"
                    "Note: Use 'execute' command to run raw TypeQL queries without API key."
                )
            self.anthropic = anthropic.Anthropic(api_key=self.api_key)

    def translate(self, question: str, schema: str | None = None) -> str:
        """
        Translate a natural language question to TypeQL.

        Args:
            question: Natural language question
            schema: Current schema (fetched automatically if not provided)

        Returns:
            TypeQL query string
        """
        self._ensure_anthropic_client()

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

        # Basic validation - check for variables
        if "match" in typeql.lower() and "$" not in typeql:
            raise ValueError(
                f"Generated query is missing variables (no $ found):\n{typeql}\n\n"
                f"This is likely a bug in the query generation. "
                f"Try rephrasing your question or use the 'execute' command with a manual query."
            )

        return typeql

    def query(self, question: str) -> QueryResult:
        """
        Translate and execute a natural language query.

        Args:
            question: Natural language question

        Returns:
            QueryResult with TypeQL query and results
        """
        typeql = ""
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
                typeql=typeql,  # Preserve the query even on error
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
