# Example Output: Office Scene Analysis

This is a complete example run of the video-to-knowledge-graph pipeline on a short office scene video (approximately 3-4 seconds, scanning across an office workspace with 2 people seated at desks).

## Video Processing

**Video:** `room_video_1.mp4`
**Scene ID:** `scene_3d74953a`
**Frames Extracted:** 4 frames @ 0.5 fps

## Scene Overview

The system identified:
- **19 entities** (2 people, 3 monitors, 2 laptops, 2 chairs, desk, computer tower, whiteboard, headphones, lighting, door, wall, floor, papers, bottle)
- **18 spatial relations** (sitting_on, on, under, next_to, attached_to, wearing, in_front_of)
- **30 schema changes** (15 entity types, 7 attribute types, 8 relation types)

---

## Entities Detected

| Entity ID | Type | Key Attributes |
|-----------|------|----------------|
| person_left | person | position: "left side of office" |
| person_right | person | position: "right side of office" |
| desk_main | desk | material: wood, color: light_brown |
| monitor_left | monitor | brand: dell, color: black |
| monitor_center | monitor | color: black |
| monitor_right | monitor | brand: dell, color: black |
| laptop_left | laptop | color: black |
| laptop_right | laptop | brand: apple, color: silver |
| computer_tower | computer_tower | color: black |
| chair_left | chair | color: gray |
| chair_right | chair | color: gray |
| whiteboard | whiteboard | size: medium, mounted on wall |
| headphones_person | headphones | color: black |
| lighting_ceiling | lighting_fixture | type: linear_led, color: black |
| door_main | door | color: white |
| wall_back | wall | color: white |
| floor_main | floor | material: wood, color: light_brown |
| papers_desk | papers | type: documents |
| bottle_desk | bottle | color: orange |

## Spatial Relations Detected

| Relation Type | Subject (From) | Reference (To) |
|---------------|----------------|----------------|
| sitting_on | person_left | chair_left |
| sitting_on | person_right | chair_right |
| on | monitor_left | desk_main |
| on | monitor_center | desk_main |
| on | monitor_right | desk_main |
| on | laptop_left | desk_main |
| on | laptop_right | desk_main |
| on | papers_desk | desk_main |
| on | bottle_desk | desk_main |
| under | computer_tower | desk_main |
| next_to | monitor_left | monitor_center |
| next_to | monitor_center | monitor_right |
| next_to | chair_left | chair_right |
| attached_to | whiteboard | wall_back |
| attached_to | lighting_ceiling | wall_back |
| wearing | person_right | headphones_person |
| in_front_of | person_left | monitor_left |
| in_front_of | person_right | monitor_right |

---

## Generated TypeDB Schema

<details>
<summary>Click to expand full TypeDB schema (TypeQL)</summary>

```typeql
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

  entity person sub physical_object;
  entity desk sub physical_object;
  entity monitor sub physical_object, owns brand;
  entity computer_tower sub physical_object;
  entity chair sub physical_object;
  entity laptop sub physical_object, owns brand;
  entity whiteboard sub physical_object;
  entity lighting_fixture sub physical_object, owns type;
  entity headphones sub physical_object, owns type;
  entity door sub physical_object;
  entity wall sub physical_object;
  entity floor sub physical_object;
  entity cable sub physical_object, owns type;
  entity papers sub physical_object, owns type;
  entity bottle sub physical_object;

  relation sitting_on sub spatial_relation;
  relation attached_to sub spatial_relation;
  relation wearing sub spatial_relation;
```

</details>

---

## Sample Entity Insert Queries

<details>
<summary>Click to expand example entity inserts</summary>

```typeql
-- Person entities
insert
  $e isa person,
  has name "person_left",
  has scene_id "scene_3d74953a",
  has position_description "left side of office";

insert
  $e isa person,
  has name "person_right",
  has scene_id "scene_3d74953a",
  has position_description "right side of office";

-- Desk
insert
  $e isa desk,
  has name "desk_main",
  has scene_id "scene_3d74953a",
  has material "wood",
  has color "light_brown";

-- Monitors
insert
  $e isa monitor,
  has name "monitor_left",
  has scene_id "scene_3d74953a",
  has brand "dell",
  has color "black";

insert
  $e isa monitor,
  has name "monitor_center",
  has scene_id "scene_3d74953a",
  has color "black";

insert
  $e isa monitor,
  has name "monitor_right",
  has scene_id "scene_3d74953a",
  has brand "dell",
  has color "black";

-- Laptops
insert
  $e isa laptop,
  has name "laptop_left",
  has scene_id "scene_3d74953a",
  has color "black";

insert
  $e isa laptop,
  has name "laptop_right",
  has scene_id "scene_3d74953a",
  has brand "apple",
  has color "silver";

-- Other entities...
```

</details>

## Sample Relation Insert Queries

<details>
<summary>Click to expand example relation inserts</summary>

```typeql
-- People sitting on chairs
match
  $from isa physical_object, has name "person_left";
  $to isa physical_object, has name "chair_left";
insert
  (subject: $from, reference: $to) isa sitting_on;

match
  $from isa physical_object, has name "person_right";
  $to isa physical_object, has name "chair_right";
insert
  (subject: $from, reference: $to) isa sitting_on;

-- Monitors on desk
match
  $from isa physical_object, has name "monitor_left";
  $to isa physical_object, has name "desk_main";
insert
  (subject: $from, reference: $to) isa on;

match
  $from isa physical_object, has name "monitor_center";
  $to isa physical_object, has name "desk_main";
insert
  (subject: $from, reference: $to) isa on;

-- Computer tower under desk
match
  $from isa physical_object, has name "computer_tower";
  $to isa physical_object, has name "desk_main";
insert
  (subject: $from, reference: $to) isa under;

-- Monitors next to each other
match
  $from isa physical_object, has name "monitor_left";
  $to isa physical_object, has name "monitor_center";
insert
  (subject: $from, reference: $to) isa next_to;

-- Whiteboard attached to wall
match
  $from isa physical_object, has name "whiteboard";
  $to isa physical_object, has name "wall_back";
insert
  (subject: $from, reference: $to) isa attached_to;

-- Person wearing headphones
match
  $from isa physical_object, has name "person_right";
  $to isa physical_object, has name "headphones_person";
insert
  (subject: $from, reference: $to) isa wearing;

-- People in front of monitors
match
  $from isa physical_object, has name "person_left";
  $to isa physical_object, has name "monitor_left";
insert
  (subject: $from, reference: $to) isa in_front_of;
```

</details>

---

## Results

✅ **Schema Applied Successfully**
✅ **19 entities inserted**
✅ **18 relations inserted**
✅ **Scene 'scene_3d74953a' added to database**

The knowledge graph is now ready for querying! Example queries:

```bash
# Find all monitors
>> python3 main.py query "What monitors are there?"


First few results:
  1. {'name': 'monitor_left'}
  2. {'name': 'monitor_center'}
  3. {'name': 'monitor_right'}

TypeQL:
match
  $monitor isa monitor;
fetch {
  "name": $monitor.name
};

Found 3 results:

1. {
  "name": "monitor_left"
}
2. {
  "name": "monitor_center"
}
3. {
  "name": "monitor_right"
}


# Find what's on the desk
>> python3 main.py query "What objects are on the desk?"

### Note: bad outcome! Better outcome would have used `match $desk isa desk;`, which would have actually found data!

TypeQL:
match
  $desk isa physical_object, has name "desk";
  $object isa physical_object, has name $obj_name;
  on (subject: $object, reference: $desk);
fetch { "object": $obj_name };

No results found.



# Find people in the scene
>> python3 main.py query "How many people are in the scene?"

TypeQL:
match
  $person isa person;
reduce $count = count;
fetch { "total": $count };

Found 1 results:

1. {
  "total": 2
}


# Find spatial relationships
python3 main.py query "What is the person on the right wearing?"
```
