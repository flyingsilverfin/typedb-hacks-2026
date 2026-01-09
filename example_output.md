Analyzing video: ../shared-dir/room_video_1.mp4
Scene ID: scene_3d74953a

Extracting frames (0.5 fps, max 5)...
Extracted 4 frames

Connecting to TypeDB...
Failed to initialize logging: attempted to set a logger after the logging system was already initialized
Using existing database: scene_graph

Analyzing frames with Claude...

================================================================================
DEBUG: VISION ANALYZER - PROMPT TO CLAUDE
================================================================================
Model: claude-sonnet-4-20250514
Max tokens: 4096
Number of images: 4

Prompt text:
You are analyzing a scene to extract entities, attributes, and SPATIAL RELATIONS for a knowledge graph stored in TypeDB.

CURRENT SCHEMA:
No existing schema (this is the first scene). Define all needed types.

INSTRUCTIONS:
1. Identify all objects/entities in the image(s)
2. For each entity, determine:
   - If it fits an existing type in the schema -> add to "new_data"
   - If it requires a new type or schema change -> add to "schema_changes" and "data_requiring_schema_change"

3. For attributes:
   - Use existing attribute types where applicable
   - Propose new attributes only when necessary
   - Common attributes: name, color, material, size, shape, position_description

4. For RELATIONS (CRITICAL - DO NOT SKIP):
   RELATIONS are as important as entities! Carefully identify spatial relationships between objects.

   Common spatial relations to look for:
   - on: object is placed on top of a surface (laptop on desk, cup on table)
   - under: object is underneath another (box under table, tower under desk)
   - next_to: objects are adjacent/beside each other (chair next to desk)
   - in_front_of: object is in front of another from viewer perspective
   - behind: object is behind another
   - inside/contains: object is contained within another (items in box, books in shelf)
   - attached_to: object is physically attached (lamp attached to wall)
   - sits_in/sitting_on: person is sitting in/on furniture

   For EACH relation:
   - Specify: type, from (subject entity ID), to (reference entity ID)
   - Use existing relation types when available in schema
   - If new relation type needed, define it in schema_changes as a subtype of spatial_relation (this inherits the standard subject/reference roles)

   EXAMPLES of good relations:
   - laptop on desk: {"type": "on", "from": "laptop_1", "to": "desk_main"}
   - person sits in chair: {"type": "sitting_on", "from": "person_1", "to": "chair_1"}
   - monitor next to monitor: {"type": "next_to", "from": "monitor_1", "to": "monitor_2"}

5. Entity IDs should be descriptive like "chair_1", "table_main", "lamp_desk"

RETURN VALID JSON with this exact structure:
{
  "new_data": {
    "entities": [
      {"id": "unique_id", "type": "existing_type", "attributes": {"color": "brown", "material": "wood"}}
    ],
    "relations": [
      {"type": "existing_relation", "from": "entity_id", "to": "entity_id"}
    ]
  },
  "schema_changes": {
    "new_entity_types": [
      {"name": "type_name", "parent": "entity", "owns": ["attr1", "attr2"]}
    ],
    "new_attribute_types": [
      {"name": "attr_name", "value_type": "string"}
    ],
    "new_relation_types": [
      {"name": "relation_name", "parent": "spatial_relation"}
    ],
    "modified_types": [
      {"name": "existing_type", "add_owns": ["new_attr"], "add_plays": ["new_role"]}
    ]
  },
  "data_requiring_schema_change": {
    "entities": [
      {"id": "new_entity_id", "type": "new_type", "attributes": {}}
    ],
    "relations": [
      {"type": "new_relation_type", "from": "entity_id", "to": "entity_id"}
    ]
  }
}

IMPORTANT REMINDERS:
- Extract ALL visible spatial relationships between objects
- Relations are mandatory - every scene should have multiple relations
- Common scene patterns:
  * Objects ON surfaces (monitors on desk, cups on table)
  * People SITTING in/on furniture
  * Objects NEXT TO each other
  * Objects UNDER surfaces (computer tower under desk)
- If you identify 10 entities, you should identify at least 5-10 relations

Be thorough but only include objects and relations you can clearly identify. Be conservative with schema changes - reuse existing types when reasonable.
Return ONLY valid JSON, no other text.
================================================================================


================================================================================
DEBUG: VISION ANALYZER - RESPONSE FROM CLAUDE
================================================================================
Stop reason: end_turn
Usage: Usage(cache_creation=CacheCreation(ephemeral_1h_input_tokens=0, ephemeral_5m_input_tokens=0), cache_creation_input_tokens=0, cache_read_input_tokens=0, input_tokens=5255, output_tokens=1763, server_tool_use=None, service_tier='standard')

Response text:
```json
{
  "new_data": {
    "entities": [],
    "relations": []
  },
  "schema_changes": {
    "new_entity_types": [
      {"name": "person", "parent": "entity", "owns": ["name", "position_description"]},
      {"name": "desk", "parent": "entity", "owns": ["material", "color", "size"]},
      {"name": "monitor", "parent": "entity", "owns": ["brand", "size", "color"]},
      {"name": "computer_tower", "parent": "entity", "owns": ["color", "size"]},
      {"name": "chair", "parent": "entity", "owns": ["material", "color"]},
      {"name": "laptop", "parent": "entity", "owns": ["brand", "color"]},
      {"name": "whiteboard", "parent": "entity", "owns": ["size", "position_description"]},
      {"name": "lighting_fixture", "parent": "entity", "owns": ["type", "color"]},
      {"name": "headphones", "parent": "entity", "owns": ["color", "type"]},
      {"name": "door", "parent": "entity", "owns": ["color", "material"]},
      {"name": "wall", "parent": "entity", "owns": ["color"]},
      {"name": "floor", "parent": "entity", "owns": ["material", "color"]},
      {"name": "cable", "parent": "entity", "owns": ["color", "type"]},
      {"name": "papers", "parent": "entity", "owns": ["type"]},
      {"name": "bottle", "parent": "entity", "owns": ["color", "material"]}
    ],
    "new_attribute_types": [
      {"name": "name", "value_type": "string"},
      {"name": "color", "value_type": "string"},
      {"name": "material", "value_type": "string"},
      {"name": "size", "value_type": "string"},
      {"name": "brand", "value_type": "string"},
      {"name": "position_description", "value_type": "string"},
      {"name": "type", "value_type": "string"}
    ],
    "new_relation_types": [
      {"name": "spatial_relation", "parent": "relation"},
      {"name": "on", "parent": "spatial_relation"},
      {"name": "under", "parent": "spatial_relation"},
      {"name": "next_to", "parent": "spatial_relation"},
      {"name": "sitting_on", "parent": "spatial_relation"},
      {"name": "attached_to", "parent": "spatial_relation"},
      {"name": "wearing", "parent": "spatial_relation"},
      {"name": "in_front_of", "parent": "spatial_relation"}
    ],
    "modified_types": []
  },
  "data_requiring_schema_change": {
    "entities": [
      {"id": "person_left", "type": "person", "attributes": {"position_description": "left side of office"}},
      {"id": "person_right", "type": "person", "attributes": {"position_description": "right side of office"}},
      {"id": "desk_main", "type": "desk", "attributes": {"material": "wood", "color": "light_brown"}},
      {"id": "monitor_left", "type": "monitor", "attributes": {"brand": "dell", "color": "black"}},
      {"id": "monitor_center", "type": "monitor", "attributes": {"color": "black"}},
      {"id": "monitor_right", "type": "monitor", "attributes": {"brand": "dell", "color": "black"}},
      {"id": "laptop_left", "type": "laptop", "attributes": {"color": "black"}},
      {"id": "laptop_right", "type": "laptop", "attributes": {"brand": "apple", "color": "silver"}},
      {"id": "computer_tower", "type": "computer_tower", "attributes": {"color": "black"}},
      {"id": "chair_left", "type": "chair", "attributes": {"color": "gray"}},
      {"id": "chair_right", "type": "chair", "attributes": {"color": "gray"}},
      {"id": "whiteboard", "type": "whiteboard", "attributes": {"size": "medium", "position_description": "mounted on wall"}},
      {"id": "headphones_person", "type": "headphones", "attributes": {"color": "black"}},
      {"id": "lighting_ceiling", "type": "lighting_fixture", "attributes": {"type": "linear_led", "color": "black"}},
      {"id": "door_main", "type": "door", "attributes": {"color": "white"}},
      {"id": "wall_back", "type": "wall", "attributes": {"color": "white"}},
      {"id": "floor_main", "type": "floor", "attributes": {"material": "wood", "color": "light_brown"}},
      {"id": "papers_desk", "type": "papers", "attributes": {"type": "documents"}},
      {"id": "bottle_desk", "type": "bottle", "attributes": {"color": "orange"}}
    ],
    "relations": [
      {"type": "sitting_on", "from": "person_left", "to": "chair_left"},
      {"type": "sitting_on", "from": "person_right", "to": "chair_right"},
      {"type": "on", "from": "monitor_left", "to": "desk_main"},
      {"type": "on", "from": "monitor_center", "to": "desk_main"},
      {"type": "on", "from": "monitor_right", "to": "desk_main"},
      {"type": "on", "from": "laptop_left", "to": "desk_main"},
      {"type": "on", "from": "laptop_right", "to": "desk_main"},
      {"type": "under", "from": "computer_tower", "to": "desk_main"},
      {"type": "next_to", "from": "monitor_left", "to": "monitor_center"},
      {"type": "next_to", "from": "monitor_center", "to": "monitor_right"},
      {"type": "next_to", "from": "chair_left", "to": "chair_right"},
      {"type": "attached_to", "from": "whiteboard", "to": "wall_back"},
      {"type": "attached_to", "from": "lighting_ceiling", "to": "wall_back"},
      {"type": "wearing", "from": "person_right", "to": "headphones_person"},
      {"type": "on", "from": "papers_desk", "to": "desk_main"},
      {"type": "on", "from": "bottle_desk", "to": "desk_main"},
      {"type": "in_front_of", "from": "person_left", "to": "monitor_left"},
      {"type": "in_front_of", "from": "person_right", "to": "monitor_right"}
    ]
  }
}
```
================================================================================


Analysis complete:
  - 0 entities fit existing schema
  - 19 entities require schema changes
  - 18 relations identified
  - 30 schema changes proposed

Generating initial schema...

Initial schema:
define
  # Base attribute types
  attribute name value string;
  attribute color value string;
  attribute material value string;
  attribute shape value string;
  attribute size value string;
  attribute position_description value string;
  attribute scene_id value string;

  # Base entity type
  entity physical_object,
    owns name,
    owns color,
    owns material,
    owns shape,
    owns size,
    owns position_description,
    owns scene_id;

  # Base spatial relations
  relation spatial_relation,
    relates subject,
    relates reference;

  relation on sub spatial_relation;
  relation under sub spatial_relation;
  relation next_to sub spatial_relation;
  relation in_front_of sub spatial_relation;
  relation behind sub spatial_relation;
  relation inside sub spatial_relation;
  relation contains sub spatial_relation;

  # Role players for base types
  physical_object plays spatial_relation:subject,
    plays spatial_relation:reference;

  # Scene-specific types
  attribute brand value string;
  attribute type value string;
  entity person,
    sub physical_object;
  entity desk,
    sub physical_object;
  entity monitor,
    sub physical_object,
    owns brand;
  entity computer_tower,
    sub physical_object;
  entity chair,
    sub physical_object;
  entity laptop,
    sub physical_object,
    owns brand;
  entity whiteboard,
    sub physical_object;
  entity lighting_fixture,
    sub physical_object,
    owns type;
  entity headphones,
    sub physical_object,
    owns type;
  entity door,
    sub physical_object;
  entity wall,
    sub physical_object;
  entity floor,
    sub physical_object;
  entity cable,
    sub physical_object,
    owns type;
  entity papers,
    sub physical_object,
    owns type;
  entity bottle,
    sub physical_object;
  relation sitting_on,
    sub spatial_relation;
  relation attached_to,
    sub spatial_relation;
  relation wearing,
    sub spatial_relation;

Apply initial schema? [y/N]: y

================================================================================
DEBUG: TYPEDB CLIENT - EXECUTE SCHEMA
================================================================================
TypeQL query:
define
  # Base attribute types
  attribute name value string;
  attribute color value string;
  attribute material value string;
  attribute shape value string;
  attribute size value string;
  attribute position_description value string;
  attribute scene_id value string;

  # Base entity type
  entity physical_object,
    owns name,
    owns color,
    owns material,
    owns shape,
    owns size,
    owns position_description,
    owns scene_id;

  # Base spatial relations
  relation spatial_relation,
    relates subject,
    relates reference;

  relation on sub spatial_relation;
  relation under sub spatial_relation;
  relation next_to sub spatial_relation;
  relation in_front_of sub spatial_relation;
  relation behind sub spatial_relation;
  relation inside sub spatial_relation;
  relation contains sub spatial_relation;

  # Role players for base types
  physical_object plays spatial_relation:subject,
    plays spatial_relation:reference;

  # Scene-specific types
  attribute brand value string;
  attribute type value string;
  entity person,
    sub physical_object;
  entity desk,
    sub physical_object;
  entity monitor,
    sub physical_object,
    owns brand;
  entity computer_tower,
    sub physical_object;
  entity chair,
    sub physical_object;
  entity laptop,
    sub physical_object,
    owns brand;
  entity whiteboard,
    sub physical_object;
  entity lighting_fixture,
    sub physical_object,
    owns type;
  entity headphones,
    sub physical_object,
    owns type;
  entity door,
    sub physical_object;
  entity wall,
    sub physical_object;
  entity floor,
    sub physical_object;
  entity cable,
    sub physical_object,
    owns type;
  entity papers,
    sub physical_object,
    owns type;
  entity bottle,
    sub physical_object;
  relation sitting_on,
    sub spatial_relation;
  relation attached_to,
    sub spatial_relation;
  relation wearing,
    sub spatial_relation;
================================================================================

DEBUG: Schema query executed successfully

Schema applied successfully

Inserting data...

=== INSERT QUERIES (DEBUG) ===

-- Entity 1/19: person_left
insert
  $e isa person,
  has name "person_left",
  has scene_id "scene_3d74953a",
  has position_description "left side of office";

-- Entity 2/19: person_right
insert
  $e isa person,
  has name "person_right",
  has scene_id "scene_3d74953a",
  has position_description "right side of office";

-- Entity 3/19: desk_main
insert
  $e isa desk,
  has name "desk_main",
  has scene_id "scene_3d74953a",
  has material "wood",
  has color "light_brown";

-- Entity 4/19: monitor_left
insert
  $e isa monitor,
  has name "monitor_left",
  has scene_id "scene_3d74953a",
  has brand "dell",
  has color "black";

-- Entity 5/19: monitor_center
insert
  $e isa monitor,
  has name "monitor_center",
  has scene_id "scene_3d74953a",
  has color "black";

-- Entity 6/19: monitor_right
insert
  $e isa monitor,
  has name "monitor_right",
  has scene_id "scene_3d74953a",
  has brand "dell",
  has color "black";

-- Entity 7/19: laptop_left
insert
  $e isa laptop,
  has name "laptop_left",
  has scene_id "scene_3d74953a",
  has color "black";

-- Entity 8/19: laptop_right
insert
  $e isa laptop,
  has name "laptop_right",
  has scene_id "scene_3d74953a",
  has brand "apple",
  has color "silver";

-- Entity 9/19: computer_tower
insert
  $e isa computer_tower,
  has name "computer_tower",
  has scene_id "scene_3d74953a",
  has color "black";

-- Entity 10/19: chair_left
insert
  $e isa chair,
  has name "chair_left",
  has scene_id "scene_3d74953a",
  has color "gray";

-- Entity 11/19: chair_right
insert
  $e isa chair,
  has name "chair_right",
  has scene_id "scene_3d74953a",
  has color "gray";

-- Entity 12/19: whiteboard
insert
  $e isa whiteboard,
  has name "whiteboard",
  has scene_id "scene_3d74953a",
  has size "medium",
  has position_description "mounted on wall";

-- Entity 13/19: headphones_person
insert
  $e isa headphones,
  has name "headphones_person",
  has scene_id "scene_3d74953a",
  has color "black";

-- Entity 14/19: lighting_ceiling
insert
  $e isa lighting_fixture,
  has name "lighting_ceiling",
  has scene_id "scene_3d74953a",
  has type "linear_led",
  has color "black";

-- Entity 15/19: door_main
insert
  $e isa door,
  has name "door_main",
  has scene_id "scene_3d74953a",
  has color "white";

-- Entity 16/19: wall_back
insert
  $e isa wall,
  has name "wall_back",
  has scene_id "scene_3d74953a",
  has color "white";

-- Entity 17/19: floor_main
insert
  $e isa floor,
  has name "floor_main",
  has scene_id "scene_3d74953a",
  has material "wood",
  has color "light_brown";

-- Entity 18/19: papers_desk
insert
  $e isa papers,
  has name "papers_desk",
  has scene_id "scene_3d74953a",
  has type "documents";

-- Entity 19/19: bottle_desk
insert
  $e isa bottle,
  has name "bottle_desk",
  has scene_id "scene_3d74953a",
  has color "orange";

=== END INSERT QUERIES ===


================================================================================
DEBUG: TYPEDB CLIENT - EXECUTE WRITE
================================================================================
TypeQL query:
insert
  $e isa person,
  has name "person_left",
  has scene_id "scene_3d74953a",
  has position_description "left side of office";
================================================================================

DEBUG: Write query executed successfully (1 results)


================================================================================
DEBUG: TYPEDB CLIENT - EXECUTE WRITE
================================================================================
TypeQL query:
insert
  $e isa person,
  has name "person_right",
  has scene_id "scene_3d74953a",
  has position_description "right side of office";
================================================================================

DEBUG: Write query executed successfully (1 results)


================================================================================
DEBUG: TYPEDB CLIENT - EXECUTE WRITE
================================================================================
TypeQL query:
insert
  $e isa desk,
  has name "desk_main",
  has scene_id "scene_3d74953a",
  has material "wood",
  has color "light_brown";
================================================================================

DEBUG: Write query executed successfully (1 results)


================================================================================
DEBUG: TYPEDB CLIENT - EXECUTE WRITE
================================================================================
TypeQL query:
insert
  $e isa monitor,
  has name "monitor_left",
  has scene_id "scene_3d74953a",
  has brand "dell",
  has color "black";
================================================================================

DEBUG: Write query executed successfully (1 results)


================================================================================
DEBUG: TYPEDB CLIENT - EXECUTE WRITE
================================================================================
TypeQL query:
insert
  $e isa monitor,
  has name "monitor_center",
  has scene_id "scene_3d74953a",
  has color "black";
================================================================================

DEBUG: Write query executed successfully (1 results)


================================================================================
DEBUG: TYPEDB CLIENT - EXECUTE WRITE
================================================================================
TypeQL query:
insert
  $e isa monitor,
  has name "monitor_right",
  has scene_id "scene_3d74953a",
  has brand "dell",
  has color "black";
================================================================================

DEBUG: Write query executed successfully (1 results)


================================================================================
DEBUG: TYPEDB CLIENT - EXECUTE WRITE
================================================================================
TypeQL query:
insert
  $e isa laptop,
  has name "laptop_left",
  has scene_id "scene_3d74953a",
  has color "black";
================================================================================

DEBUG: Write query executed successfully (1 results)


================================================================================
DEBUG: TYPEDB CLIENT - EXECUTE WRITE
================================================================================
TypeQL query:
insert
  $e isa laptop,
  has name "laptop_right",
  has scene_id "scene_3d74953a",
  has brand "apple",
  has color "silver";
================================================================================

DEBUG: Write query executed successfully (1 results)


================================================================================
DEBUG: TYPEDB CLIENT - EXECUTE WRITE
================================================================================
TypeQL query:
insert
  $e isa computer_tower,
  has name "computer_tower",
  has scene_id "scene_3d74953a",
  has color "black";
================================================================================

DEBUG: Write query executed successfully (1 results)


================================================================================
DEBUG: TYPEDB CLIENT - EXECUTE WRITE
================================================================================
TypeQL query:
insert
  $e isa chair,
  has name "chair_left",
  has scene_id "scene_3d74953a",
  has color "gray";
================================================================================

DEBUG: Write query executed successfully (1 results)


================================================================================
DEBUG: TYPEDB CLIENT - EXECUTE WRITE
================================================================================
TypeQL query:
insert
  $e isa chair,
  has name "chair_right",
  has scene_id "scene_3d74953a",
  has color "gray";
================================================================================

DEBUG: Write query executed successfully (1 results)


================================================================================
DEBUG: TYPEDB CLIENT - EXECUTE WRITE
================================================================================
TypeQL query:
insert
  $e isa whiteboard,
  has name "whiteboard",
  has scene_id "scene_3d74953a",
  has size "medium",
  has position_description "mounted on wall";
================================================================================

DEBUG: Write query executed successfully (1 results)


================================================================================
DEBUG: TYPEDB CLIENT - EXECUTE WRITE
================================================================================
TypeQL query:
insert
  $e isa headphones,
  has name "headphones_person",
  has scene_id "scene_3d74953a",
  has color "black";
================================================================================

DEBUG: Write query executed successfully (1 results)


================================================================================
DEBUG: TYPEDB CLIENT - EXECUTE WRITE
================================================================================
TypeQL query:
insert
  $e isa lighting_fixture,
  has name "lighting_ceiling",
  has scene_id "scene_3d74953a",
  has type "linear_led",
  has color "black";
================================================================================

DEBUG: Write query executed successfully (1 results)


================================================================================
DEBUG: TYPEDB CLIENT - EXECUTE WRITE
================================================================================
TypeQL query:
insert
  $e isa door,
  has name "door_main",
  has scene_id "scene_3d74953a",
  has color "white";
================================================================================

DEBUG: Write query executed successfully (1 results)


================================================================================
DEBUG: TYPEDB CLIENT - EXECUTE WRITE
================================================================================
TypeQL query:
insert
  $e isa wall,
  has name "wall_back",
  has scene_id "scene_3d74953a",
  has color "white";
================================================================================

DEBUG: Write query executed successfully (1 results)


================================================================================
DEBUG: TYPEDB CLIENT - EXECUTE WRITE
================================================================================
TypeQL query:
insert
  $e isa floor,
  has name "floor_main",
  has scene_id "scene_3d74953a",
  has material "wood",
  has color "light_brown";
================================================================================

DEBUG: Write query executed successfully (1 results)


================================================================================
DEBUG: TYPEDB CLIENT - EXECUTE WRITE
================================================================================
TypeQL query:
insert
  $e isa papers,
  has name "papers_desk",
  has scene_id "scene_3d74953a",
  has type "documents";
================================================================================

DEBUG: Write query executed successfully (1 results)


================================================================================
DEBUG: TYPEDB CLIENT - EXECUTE WRITE
================================================================================
TypeQL query:
insert
  $e isa bottle,
  has name "bottle_desk",
  has scene_id "scene_3d74953a",
  has color "orange";
================================================================================

DEBUG: Write query executed successfully (1 results)


================================================================================
DEBUG: TYPEDB CLIENT - EXECUTE WRITE
================================================================================
TypeQL query:
match
  $from isa physical_object, has name "person_left";
  $to isa physical_object, has name "chair_left";
insert
  (subject: $from, reference: $to) isa sitting_on;
================================================================================

DEBUG: Write query executed successfully (1 results)


================================================================================
DEBUG: TYPEDB CLIENT - EXECUTE WRITE
================================================================================
TypeQL query:
match
  $from isa physical_object, has name "person_right";
  $to isa physical_object, has name "chair_right";
insert
  (subject: $from, reference: $to) isa sitting_on;
================================================================================

DEBUG: Write query executed successfully (1 results)


================================================================================
DEBUG: TYPEDB CLIENT - EXECUTE WRITE
================================================================================
TypeQL query:
match
  $from isa physical_object, has name "monitor_left";
  $to isa physical_object, has name "desk_main";
insert
  (subject: $from, reference: $to) isa on;
================================================================================

DEBUG: Write query executed successfully (1 results)


================================================================================
DEBUG: TYPEDB CLIENT - EXECUTE WRITE
================================================================================
TypeQL query:
match
  $from isa physical_object, has name "monitor_center";
  $to isa physical_object, has name "desk_main";
insert
  (subject: $from, reference: $to) isa on;
================================================================================

DEBUG: Write query executed successfully (1 results)


================================================================================
DEBUG: TYPEDB CLIENT - EXECUTE WRITE
================================================================================
TypeQL query:
match
  $from isa physical_object, has name "monitor_right";
  $to isa physical_object, has name "desk_main";
insert
  (subject: $from, reference: $to) isa on;
================================================================================

DEBUG: Write query executed successfully (1 results)


================================================================================
DEBUG: TYPEDB CLIENT - EXECUTE WRITE
================================================================================
TypeQL query:
match
  $from isa physical_object, has name "laptop_left";
  $to isa physical_object, has name "desk_main";
insert
  (subject: $from, reference: $to) isa on;
================================================================================

DEBUG: Write query executed successfully (1 results)


================================================================================
DEBUG: TYPEDB CLIENT - EXECUTE WRITE
================================================================================
TypeQL query:
match
  $from isa physical_object, has name "laptop_right";
  $to isa physical_object, has name "desk_main";
insert
  (subject: $from, reference: $to) isa on;
================================================================================

DEBUG: Write query executed successfully (1 results)


================================================================================
DEBUG: TYPEDB CLIENT - EXECUTE WRITE
================================================================================
TypeQL query:
match
  $from isa physical_object, has name "computer_tower";
  $to isa physical_object, has name "desk_main";
insert
  (subject: $from, reference: $to) isa under;
================================================================================

DEBUG: Write query executed successfully (1 results)


================================================================================
DEBUG: TYPEDB CLIENT - EXECUTE WRITE
================================================================================
TypeQL query:
match
  $from isa physical_object, has name "monitor_left";
  $to isa physical_object, has name "monitor_center";
insert
  (subject: $from, reference: $to) isa next_to;
================================================================================

DEBUG: Write query executed successfully (1 results)


================================================================================
DEBUG: TYPEDB CLIENT - EXECUTE WRITE
================================================================================
TypeQL query:
match
  $from isa physical_object, has name "monitor_center";
  $to isa physical_object, has name "monitor_right";
insert
  (subject: $from, reference: $to) isa next_to;
================================================================================

DEBUG: Write query executed successfully (1 results)


================================================================================
DEBUG: TYPEDB CLIENT - EXECUTE WRITE
================================================================================
TypeQL query:
match
  $from isa physical_object, has name "chair_left";
  $to isa physical_object, has name "chair_right";
insert
  (subject: $from, reference: $to) isa next_to;
================================================================================

DEBUG: Write query executed successfully (1 results)


================================================================================
DEBUG: TYPEDB CLIENT - EXECUTE WRITE
================================================================================
TypeQL query:
match
  $from isa physical_object, has name "whiteboard";
  $to isa physical_object, has name "wall_back";
insert
  (subject: $from, reference: $to) isa attached_to;
================================================================================

DEBUG: Write query executed successfully (1 results)


================================================================================
DEBUG: TYPEDB CLIENT - EXECUTE WRITE
================================================================================
TypeQL query:
match
  $from isa physical_object, has name "lighting_ceiling";
  $to isa physical_object, has name "wall_back";
insert
  (subject: $from, reference: $to) isa attached_to;
================================================================================

DEBUG: Write query executed successfully (1 results)


================================================================================
DEBUG: TYPEDB CLIENT - EXECUTE WRITE
================================================================================
TypeQL query:
match
  $from isa physical_object, has name "person_right";
  $to isa physical_object, has name "headphones_person";
insert
  (subject: $from, reference: $to) isa wearing;
================================================================================

DEBUG: Write query executed successfully (1 results)


================================================================================
DEBUG: TYPEDB CLIENT - EXECUTE WRITE
================================================================================
TypeQL query:
match
  $from isa physical_object, has name "papers_desk";
  $to isa physical_object, has name "desk_main";
insert
  (subject: $from, reference: $to) isa on;
================================================================================

DEBUG: Write query executed successfully (1 results)


================================================================================
DEBUG: TYPEDB CLIENT - EXECUTE WRITE
================================================================================
TypeQL query:
match
  $from isa physical_object, has name "bottle_desk";
  $to isa physical_object, has name "desk_main";
insert
  (subject: $from, reference: $to) isa on;
================================================================================

DEBUG: Write query executed successfully (1 results)


================================================================================
DEBUG: TYPEDB CLIENT - EXECUTE WRITE
================================================================================
TypeQL query:
match
  $from isa physical_object, has name "person_left";
  $to isa physical_object, has name "monitor_left";
insert
  (subject: $from, reference: $to) isa in_front_of;
================================================================================

DEBUG: Write query executed successfully (1 results)


================================================================================
DEBUG: TYPEDB CLIENT - EXECUTE WRITE
================================================================================
TypeQL query:
match
  $from isa physical_object, has name "person_right";
  $to isa physical_object, has name "monitor_right";
insert
  (subject: $from, reference: $to) isa in_front_of;
================================================================================

DEBUG: Write query executed successfully (1 results)

Inserted 19 entities
Inserted 18 relations

Done! Scene 'scene_3d74953a' added to database.
