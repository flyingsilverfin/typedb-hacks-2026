# Scene Understanding with TypeDB - Hackathon Plan

## Implementation Progress

| Component | Status | File |
|-----------|--------|------|
| Project structure | DONE | `src/`, `prompts/` |
| Requirements | DONE | `requirements.txt` |
| TypeDB client wrapper | DONE | `src/typedb_client.py` |
| Video frame extractor | DONE | `src/video_processor.py` |
| Vision analyzer (Claude) | DONE | `src/vision_analyzer.py` |
| Schema generator | DONE | `src/schema_generator.py` |
| Schema migrator | DONE | `src/schema_migrator.py` |
| Data inserter | DONE | `src/data_inserter.py` |
| Query translator | DONE | `src/query_translator.py` |
| CLI interface | DONE | `main.py` |
| Prompt templates | DONE | `prompts/*.txt` |
| End-to-end testing | TODO | Need Python environment |

### Next Steps
1. Install dependencies: `pip install -r requirements.txt`
2. Start TypeDB server: `./typedb-all-linux-arm64-3.7.2/typedb server`
3. Set environment variable: `export ANTHROPIC_API_KEY=your_key`
4. Test with a video: `python main.py analyze <video.mp4>`
5. Query the scene: `python main.py query "What objects are in the room?"`

### CLI Commands
```bash
python main.py analyze <video>    # Analyze video, create/update schema, insert data
python main.py query "<question>" # Natural language query
python main.py execute "<typeql>" # Raw TypeQL query
python main.py schema             # Show current schema
python main.py clear              # Delete database
python main.py info               # Show database info
```

---

## Overview
Build a system that takes a video of a room, uses Claude's vision to extract entities/relations/attributes, generates a TypeDB schema, populates the database, and enables natural language queries translated to TypeQL.

**Key Feature**: Support incremental schema evolution when new scenes are added. The system detects when new scenes require schema changes and handles migrations automatically.

## Architecture

```
┌─────────────┐    ┌──────────────┐    ┌─────────────────────────────────────┐
│   Video     │───▶│ Frame        │───▶│ Claude Vision Analysis              │
│   Input     │    │ Extractor    │    │ (receives current schema as context)│
└─────────────┘    └──────────────┘    └──────────────┬──────────────────────┘
                                                      │
                                       ┌──────────────┴──────────────┐
                                       ▼                              ▼
                              ┌────────────────┐            ┌─────────────────┐
                              │ New Data       │            │ Schema Changes  │
                              │ (fits schema)  │            │ (mutations)     │
                              └───────┬────────┘            └────────┬────────┘
                                      │                              │
                                      │         ┌────────────────────┘
                                      │         ▼
                                      │  ┌─────────────────┐
                                      │  │ Schema Migrator │
                                      │  │ - define new    │
                                      │  │ - redefine      │
                                      │  │ - undefine      │
                                      │  │ - migrate data  │
                                      │  └────────┬────────┘
                                      │           │
                                      ▼           ▼
                              ┌─────────────────────────┐
                              │       TypeDB            │
                              └─────────────────────────┘
                                          ▲
                                          │
┌─────────────┐    ┌──────────────┐       │
│   CLI       │◀──▶│ NL→TypeQL   │───────┘
│   Interface │    │ Translator   │
└─────────────┘    └──────────────┘
```

## Tech Stack
- **Language**: Python 3.11+
- **Video Processing**: OpenCV (cv2)
- **LLM**: Claude API (Anthropic SDK)
- **Database**: TypeDB 3.7.2 (already installed)
- **TypeDB Driver**: typedb-driver (Python)

> **IMPORTANT**: Always use TypeDB 3.0 syntax throughout. TypeDB 3.x has significant syntax changes from 2.x. Key differences include: `entity`/`relation`/`attribute` keywords before type names, `value` for attribute types, and updated driver API with `Credentials`, `DriverOptions`, and `TransactionType`.

## TypeDB 3.x Reference (Key Syntax)

### Python Driver Connection
```python
from typedb.driver import TypeDB, Credentials, DriverOptions, TransactionType

address = "localhost:1729"
credentials = Credentials("admin", "password")
options = DriverOptions(is_tls_enabled=False, tls_root_ca_path=None)

with TypeDB.driver(address, credentials, options) as driver:
    # Create database
    driver.databases.create("scene_graph")

    # Schema transaction
    with driver.transaction("scene_graph", TransactionType.SCHEMA) as tx:
        tx.query("define entity person;").resolve()
        tx.commit()

    # Write transaction
    with driver.transaction("scene_graph", TransactionType.WRITE) as tx:
        tx.query("insert $p isa person;").resolve()
        tx.commit()

    # Read transaction
    with driver.transaction("scene_graph", TransactionType.READ) as tx:
        result = tx.query("match $p isa person; fetch { 'person': $p };").resolve()
        for doc in result.as_concept_documents():
            print(doc)
```

### Schema Definition (define)
```typeql
define
  # Attribute types with value types
  attribute color value string;
  attribute material value string;
  attribute name value string;
  attribute position_x value double;
  attribute position_y value double;

  # Entity types with ownership
  entity physical_object,
    owns name,
    owns color,
    owns material,
    owns position_x,
    owns position_y;

  entity furniture sub physical_object;
  entity chair sub furniture;
  entity table sub furniture;

  # Relation types with roles
  relation spatial_relation,
    relates subject,
    relates reference;

  relation on sub spatial_relation;
  relation next_to sub spatial_relation;

  # Role players
  physical_object plays spatial_relation:subject,
    plays spatial_relation:reference;
```

### Schema Modification (redefine)

**IMPORTANT**: `redefine` is ONLY for modifying existing definitions, NOT for adding new ones.
Use `define` for additive changes (new types, new owns/plays). Use `redefine` for:
- Changing a type's supertype (`sub`)
- Changing an attribute's value type
- Changing role specialization (`relates ... as`)
- Updating annotation arguments

```typeql
# Change a type's supertype
redefine user sub page;

# Change attribute value type
redefine height value double;

# Update annotation arguments
redefine email value string @regex("^.*@typedb\.com$");
redefine post owns tag @card(0..5);

# Change role specialization
redefine fathership relates father as parent;
```

### Adding to Existing Types (use define, not redefine)
```typeql
# Add new attribute type
define attribute brand value string;

# Add ownership to existing type (additive = use define)
define furniture owns brand;

# Add role player to existing type
define furniture plays contains:container;
```

### Schema Removal (undefine)
```typeql
# Remove a type
undefine obsolete_type;

# Remove ownership from type
undefine owns old_attribute from furniture;

# Remove role from relation
undefine relates old_role from some_relation;

# Remove annotation
undefine @card from user owns email;
```

### Data Insertion (insert)
```typeql
insert
  $chair isa chair, has name "chair_1", has color "brown", has material "wood";
  $table isa table, has name "table_1", has color "white";
  $rel (subject: $chair, reference: $table) isa next_to;
```

### Data Querying (match + fetch)
```typeql
# Find all furniture with color
match
  $f isa furniture, has color $c;
fetch {
  "item": $f,
  "color": $c
};

# Find items on a table
match
  $table isa table;
  $item isa physical_object;
  (subject: $item, reference: $table) isa on;
fetch {
  "on_table": $item.*
};

# Find by attribute value
match
  $obj isa physical_object, has color "brown";
fetch {
  "brown_objects": $obj.*
};
```

### Key TypeDB 3.x Notes
- `links` keyword used for relation role players in insert (alternative syntax)
- `isa` required for all new instances
- `has` for attribute ownership
- Fetch returns JSON documents
- Annotations: `@key`, `@unique`, `@card(min..max)`, `@regex`, `@abstract`
- Define is idempotent (can run multiple times safely)
- Redefine only allows one change per query

## Project Structure

```
scene-graph/
├── main.py                 # CLI entry point
├── requirements.txt        # Dependencies
├── src/
│   ├── __init__.py
│   ├── video_processor.py  # Extract frames from video
│   ├── vision_analyzer.py  # Claude vision API for scene analysis
│   ├── schema_generator.py # Generate initial TypeDB schema
│   ├── schema_migrator.py  # Handle schema evolution & data migration
│   ├── data_inserter.py    # Insert data into TypeDB
│   ├── query_translator.py # Natural language to TypeQL
│   └── typedb_client.py    # TypeDB connection wrapper
├── prompts/
│   ├── scene_analysis.txt  # Prompt for extracting entities/relations
│   └── query_translation.txt # Prompt for NL→TypeQL
└── examples/
    └── sample_schema.tql   # Example TypeDB schema for reference
```

## Core Data Structures

### LLM Analysis Output (Schema-Aware)

When analyzing a new scene, the LLM receives the current schema and returns:

```json
{
  "new_data": {
    "entities": [
      {"id": "chair_1", "type": "chair", "attributes": {"color": "brown", "material": "wood"}}
    ],
    "relations": [
      {"type": "next_to", "from": "chair_1", "to": "table_1"}
    ]
  },
  "schema_changes": {
    "new_entity_types": [
      {
        "name": "plant",
        "parent": "entity",
        "owns": ["species", "height"]
      }
    ],
    "new_attribute_types": [
      {"name": "species", "value_type": "string"},
      {"name": "height", "value_type": "double"}
    ],
    "new_relation_types": [
      {
        "name": "contains",
        "roles": [
          {"name": "container", "plays": ["pot", "vase", "box"]},
          {"name": "contained", "plays": ["plant", "item"]}
        ]
      }
    ],
    "modified_types": [
      {
        "name": "furniture",
        "add_owns": ["brand"],
        "add_plays": ["container"]
      }
    ],
    "removed_types": []
  },
  "data_requiring_schema_change": [
    {"id": "plant_1", "type": "plant", "attributes": {"species": "fern", "height": 0.5}},
    {"id": "pot_1", "type": "pot", "attributes": {"color": "terracotta"}}
  ]
}
```

### Schema Migration Operations

The migrator processes schema changes into ordered operations:

```python
@dataclass
class SchemaOperation:
    operation: Literal["define", "redefine", "undefine"]
    typeql: str
    description: str
    requires_data_migration: bool = False
    migration_queries: list[str] = None  # For data migration if needed
```

## Implementation Steps

### Step 1: Project Setup
- Create directory structure
- Create `requirements.txt` with dependencies

### Step 2: Video Frame Extraction (`video_processor.py`)
- Accept video file path
- Extract frames at configurable intervals (e.g., 1 frame per second)
- Return list of frames as base64-encoded images for Claude API
- Handle common video formats (mp4, mov, avi)

### Step 3: Vision Analysis (`vision_analyzer.py`)

**Key Change**: The analyzer now receives the current schema as context.

```python
def analyze_scene(frames: list[bytes], current_schema: str | None = None) -> AnalysisResult:
    """
    Analyze frames with schema context.

    If current_schema is None (first scene): Extract all entities freely
    If current_schema exists:
      - Use existing types where applicable
      - Identify new data that fits schema
      - Identify entities/relations that require schema changes
    """
```

The prompt includes:
1. Current schema (if exists)
2. Instructions to categorize output into "fits schema" vs "requires changes"
3. Guidelines for proposing schema modifications

### Step 4: Schema Generator (`schema_generator.py`)
- For initial scene: Generate complete schema from scratch
- Converts entity/relation/attribute types to TypeQL `define` statements

### Step 5: Schema Migrator (`schema_migrator.py`)

**New module** for handling schema evolution:

```python
class SchemaMigrator:
    def __init__(self, typedb_client):
        self.client = typedb_client

    def plan_migration(self, schema_changes: dict) -> list[SchemaOperation]:
        """
        Convert schema changes into ordered operations.
        Handles dependencies (e.g., define attributes before entities that own them)
        """

    def execute_migration(self, operations: list[SchemaOperation]) -> MigrationResult:
        """
        Execute schema operations in order.
        Handles rollback on failure.
        """

    def migrate_data(self, old_type: str, new_type: str, transform: dict):
        """
        Migrate existing data when types change.
        E.g., if 'chair' is reclassified as 'seating', update existing chairs.
        """
```

**Migration Scenarios**:

1. **Add new entity type**: Simple `define` statement
   ```typeql
   define
     attribute species value string;
     attribute height value double;
     entity plant, owns species, owns height;
   ```

2. **Add attribute to existing type**: Use `define` (additive change)
   ```typeql
   define
     attribute brand value string;
     furniture owns brand;
   ```

3. **Add new relation type**: `define` with role players
   ```typeql
   define
     relation contains, relates container, relates contained;
     pot plays contains:container;
     plant plays contains:contained;
   ```

4. **Rename/reclassify entity type**: Requires data migration
   ```python
   # 1. Define new type
   # 2. Query existing data
   # 3. Insert as new type
   # 4. Delete old data
   # 5. Undefine old type (if no longer needed)
   ```

5. **Change attribute value type**: Requires data migration
   ```python
   # E.g., height: string -> double
   # 1. Define new attribute
   # 2. Query existing values, convert
   # 3. Update entities with new attribute
   # 4. Remove old attribute ownership
   ```

### Step 6: TypeDB Client (`typedb_client.py`)
- Connection management to TypeDB server
- Create database if not exists
- **Get current schema** (for providing to LLM)
- Execute schema definitions/redefinitions/undefinitions
- Execute data insertions
- Execute queries
- Transaction management for migrations

```python
class TypeDBClient:
    def get_schema(self) -> str:
        """Return current schema as TypeQL string"""

    def execute_schema(self, typeql: str, operation: str = "define"):
        """Execute define/redefine/undefine"""

    def execute_in_transaction(self, operations: list[Callable]):
        """Execute multiple operations atomically"""
```

### Step 7: Data Insertion (`data_inserter.py`)
- Convert extracted entities to TypeQL insert statements
- Insert entities with attributes
- Insert relations between entities
- **Now called after schema migration completes**

### Step 8: Query Translation (`query_translator.py`)
- Accept natural language questions
- Use Claude to translate to TypeQL
- Provide schema context to Claude for accurate translation
- Execute query and return results

### Step 9: CLI Interface (`main.py`)

Commands:
- `python main.py analyze <video_path>` - Process video and populate database
  - If schema exists: Show proposed changes, ask for confirmation
- `python main.py query "<question>"` - Ask questions about the scene
- `python main.py schema` - Show current schema
- `python main.py history` - Show schema evolution history
- `python main.py clear` - Clear database

**New analyze flow**:
```
$ python main.py analyze kitchen.mp4

Analyzing video... extracted 15 frames
Current schema has 5 entity types, 8 attributes, 3 relations

Analysis complete:
  - 12 new entities fit existing schema
  - 3 entities require schema changes

Proposed schema changes:
  1. [DEFINE] New attribute: brand (string)
  2. [DEFINE] New entity type: appliance
  3. [DEFINE] furniture owns brand (additive)
  4. [DEFINE] New relation: plugged_into

Proceed with migration? [y/n]: y

Executing migration...
  ✓ Defined attribute 'brand'
  ✓ Defined entity 'appliance'
  ✓ Redefined 'furniture' to own 'brand'
  ✓ Defined relation 'plugged_into'

Inserting data...
  ✓ Inserted 15 entities
  ✓ Inserted 8 relations

Done! Database now has 20 entities across 6 types.
```

## Key Prompts

### Scene Analysis Prompt (Schema-Aware)
```
You are analyzing a scene to extract entities, attributes, and relations for a knowledge graph.

CURRENT SCHEMA:
{schema_or_none}

INSTRUCTIONS:
1. Identify all objects/entities in the image
2. For each entity, determine:
   - If it fits an existing type in the schema → add to "new_data"
   - If it requires a new type or schema change → add to "schema_changes" and "data_requiring_schema_change"

3. For attributes:
   - Use existing attribute types where applicable
   - Propose new attributes only when necessary

4. For relations:
   - Use existing relation types where applicable
   - Propose new relation types for spatial/functional relationships not covered

RETURN JSON:
{
  "new_data": {
    "entities": [{"id": "...", "type": "existing_type", "attributes": {...}}],
    "relations": [{"type": "existing_relation", "from": "id", "to": "id", "roles": {...}}]
  },
  "schema_changes": {
    "new_entity_types": [...],
    "new_attribute_types": [...],
    "new_relation_types": [...],
    "modified_types": [...],
    "removed_types": []
  },
  "data_requiring_schema_change": [...]
}

Be conservative with schema changes - reuse existing types when reasonable.
```

### Query Translation Prompt
```
Given this TypeDB schema:
{schema}

Translate this natural language question to TypeQL:
"{question}"

Return only the TypeQL query, no explanation.
```

## Verification Plan
1. Start TypeDB server: `./typedb-all-linux-arm64-3.7.2/typedb server`
2. **Scene 1**: Analyze a living room video
   - Verify initial schema created
   - Test basic queries
3. **Scene 2**: Analyze a kitchen video
   - Verify schema changes proposed (new types like appliance)
   - Confirm migration executes correctly
   - Test queries spanning both scenes
4. **Scene 3**: Analyze an office video
   - Verify incremental schema evolution
   - Test complex queries across all scenes

Test queries:
- `python main.py query "What objects are in the room?"`
- `python main.py query "What appliances are in the kitchen?"`
- `python main.py query "What is on tables across all scenes?"`

## Files to Create
1. `requirements.txt`
2. `main.py`
3. `src/__init__.py`
4. `src/video_processor.py`
5. `src/vision_analyzer.py`
6. `src/schema_generator.py`
7. `src/schema_migrator.py` ← NEW
8. `src/data_inserter.py`
9. `src/query_translator.py`
10. `src/typedb_client.py`
11. `prompts/scene_analysis.txt`
12. `prompts/query_translation.txt`

## Dependencies
```
anthropic>=0.40.0
opencv-python>=4.9.0
typedb-driver>=3.0.0  # TypeDB 3.x driver
click>=8.1.0
```

## Environment Variables Required
- `ANTHROPIC_API_KEY` - Your Claude API key

## Open Questions / Future Enhancements
1. **Conflict resolution**: What if two scenes suggest contradictory schema changes?
2. **Entity deduplication**: Same object in multiple scenes (e.g., "the same chair")
3. **Schema versioning**: Track schema history for rollback
4. **Dry-run mode**: Preview all changes without executing
