"""Query translator for converting natural language to TypeQL."""

import json
import os
from dataclasses import dataclass
from typing import Any

import anthropic

from .typedb_client import TypeDBClient


QUERY_TRANSLATION_PROMPT = """You are a TypeQL 3.0 query generator for TypeDB. Convert natural language questions to TypeQL queries.

# TYPEQL 3.0 REFERENCE

## Core Syntax Rules
- ALL variables must start with $ (e.g., $user, $name, $age)
- Comments start with # and continue to end of line
- Statements end with semicolons
- Relations use: relation_type (role: $player, role: $player); OR $rel isa relation_type, links (role: $player);

## Reserved Keywords (NEVER use as identifiers):
with, match, fetch, update, define, undefine, redefine, insert, put, delete, end, entity, relation, attribute, role, asc, desc, struct, fun, return, alias, sub, owns, as, plays, relates, iid, isa, links, has, is, or, not, try, in, true, false, of, from, first, last

## Query Pipeline Stages

### Match Stage - Find Data
Syntax: match <pattern>;
Example:
match
  $user isa user, has username "user_0";
  friendship (friend: $user, friend: $friend);

### Fetch Stage - Retrieve and Format Data
Syntax: fetch {{ <structure> }};
Features:
- JSON-like nested structures
- Attribute access: $var.attribute_name for single value, [$var.attribute_name] for multiple values
- All attributes: {{ $var.* }}
- Subqueries: [] for multiple results, () for single result

Example:
fetch {{
  "name": $user.username,
  "all_attrs": {{ $user.* }},
  "emails": [$user.email]
}};

### Stream Control Operators
- select $var1, $var2; - Filter which variables to return
- sort $var [asc/desc]; - Order results
- limit <number>; - Restrict result count
- offset <number>; - Skip first N results

### Reduce Stage - Aggregations
Syntax: reduce $result = <function> [groupby $vars];
Functions: count, sum, mean, max, min
Example:
reduce $friend_count = count groupby $user;

## Pattern Construction

### Basic Data Patterns
- Type assertion: $x isa person;
- Attribute ownership: $x has name $n; OR $x has name "John";
- Anonymous relation: friendship (friend: $x, friend: $y);
- Variablized relation: $rel isa friendship, links (friend: $x, friend: $y);
- Value comparison: $age > 25;
- Concept equality: $x is $y;

### Logical Operators
- Conjunction: and (implicit with ; or ,)
- Disjunction: {{pattern}} or {{pattern}}
- Negation: not {{ pattern }}
- Optionality: try {{ pattern }}

### Comparison Operators
Equality: =, !=
Ordering: <, <=, >, >=
Pattern matching: like, contains

## Common Query Patterns

### Find entities by type and attribute
match
  $obj isa entity_type, has attribute_name $value;
fetch {{ "value": $value }};

### Find entities with specific attribute value
match
  $obj isa entity_type, has name $n, has color "red";
fetch {{ "name": $n }};

### Query relations (anonymous form - when you don't need the relation variable)
match
  $subject isa subject_type, has name $subj_name;
  $reference isa reference_type, has name $ref_name;
  relation_type (subject_role: $subject, reference_role: $reference);
fetch {{ "from": $subj_name, "to": $ref_name }};

### Query relations (variablized form - when you need the relation variable)
match
  $subject isa subject_type, has name $subj_name;
  $reference isa reference_type, has name $ref_name;
  $rel isa relation_type, links (subject_role: $subject, reference_role: $reference);
fetch {{ "from": $subj_name, "to": $ref_name }};

### Count aggregation
match
  $obj isa entity_type;
reduce $count = count;
fetch {{ "total": $count }};

### Count with grouping
match
  $obj isa entity_type, has category $cat;
reduce $count = count groupby $cat;
fetch {{ "category": $cat, "count": $count }};

### Sorting and limiting
match
  $obj isa entity_type, has name $n, has score $s;
sort $s desc;
limit 10;
fetch {{ "name": $n, "score": $s }};

### Subtype querying
match
  $obj isa parent_type;  # Includes all subtypes
fetch {{ "name": $obj.name }};

## Critical Rules for Query Generation

1. **ALWAYS use variables** - Never omit $ prefix
   ❌ match isa person;
   ✅ match $p isa person;

2. **ALWAYS use variables for attributes in match**
   ❌ match $p has name;
   ✅ match $p has name $n;

3. **ONLY fetch attribute variables, NOT entity/relation variables**
   ❌ fetch {{ "person": $p }};
   ✅ fetch {{ "name": $p.name }};
   ✅ fetch {{ "name": $n }};  (if $n was bound with has name $n)

4. **Use correct relation syntax**
   ✅ relation_type (role: $var1, role: $var2);
   ✅ $rel isa relation_type, links (role: $var1, role: $var2);
   ❌ ($role: $var1, $role: $var2) isa relation_type;  (TypeQL 2.0 syntax - wrong!)

5. **Separate multiple has clauses**
   ✅ $p has name $n, has age $a;
   ✅ $p has name $n; $p has age $a;

6. **Use fetch for output, not select (unless you need to filter variables)**
   - select: Filters which variables flow through pipeline
   - fetch: Formats final output as JSON

# CURRENT SCHEMA
{schema}

# YOUR TASK
Convert this natural language question to a TypeQL query:

QUESTION: {question}

INSTRUCTIONS:
1. **USE SCHEMA TYPES SEMANTICALLY** - Don't guess attribute values!
   - If question asks "What monitors are there?" → Use `$x isa monitor` (entity type from schema)
   - If question asks "What is on the desk?" → Use `on (subject: $x, reference: $desk)` (relation type from schema)
   - If question asks "What chairs are there?" → Use `$x isa chair` (not "has type 'chair'")

2. **Prioritize semantic types over attribute filtering:**
   - First check if question words match entity types, relation types, or role names in schema
   - Only filter by attributes when question explicitly mentions attribute values (e.g., "black monitors", "wooden chairs")

3. Analyze the question to identify: entities, attributes, relations, filters, aggregations

4. Build the match pattern with proper variables

5. Add stream control (select/sort/limit) if needed

6. Add reduce stage if aggregation is needed

7. Build the fetch structure for output

8. Return ONLY the TypeQL query - no explanation, no markdown formatting

Return the query now:"""


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
        model: str = "claude-sonnet-4-20250514",
        debug: bool = False
    ):
        """
        Initialize query translator.

        Args:
            client: TypeDB client for executing queries
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Claude model to use
            debug: Enable verbose debug logging
        """
        self.client = client
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.anthropic = None
        self.model = model
        self.debug = debug

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

        if self.debug:
            print("\n" + "="*80)
            print("DEBUG: QUERY TRANSLATOR - PROMPT TO CLAUDE")
            print("="*80)
            print(f"Model: {self.model}")
            print(f"Max tokens: 1024")
            print(f"Question: {question}")
            print("\nFull prompt:")
            print(prompt)
            print("="*80 + "\n")

        response = self.anthropic.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        typeql = response.content[0].text.strip()

        if self.debug:
            print("\n" + "="*80)
            print("DEBUG: QUERY TRANSLATOR - RESPONSE FROM CLAUDE")
            print("="*80)
            print(f"Stop reason: {response.stop_reason}")
            print(f"Usage: {response.usage}")
            print("\nGenerated TypeQL:")
            print(typeql)
            print("="*80 + "\n")

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
