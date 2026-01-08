"""Schema generator for creating TypeDB schema from analysis results."""

from dataclasses import dataclass, field
from typing import Any

from .vision_analyzer import AnalysisResult, SchemaChange


@dataclass
class SchemaDefinition:
    """Complete schema definition ready for TypeDB."""
    attribute_types: list[dict[str, Any]] = field(default_factory=list)
    entity_types: list[dict[str, Any]] = field(default_factory=list)
    relation_types: list[dict[str, Any]] = field(default_factory=list)
    role_players: list[dict[str, Any]] = field(default_factory=list)


# Default base schema with common types
BASE_SCHEMA = """define
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
"""


class SchemaGenerator:
    """Generate TypeDB schema from analysis results."""

    # Mapping from LLM value types to TypeDB value types
    VALUE_TYPE_MAP = {
        "string": "string",
        "str": "string",
        "integer": "integer",
        "int": "integer",
        "double": "double",
        "float": "double",
        "boolean": "boolean",
        "bool": "boolean",
        "datetime": "datetime",
        "date": "date",
    }

    # TypeQL reserved keywords that need to be renamed
    RESERVED_KEYWORDS = {
        "in": "contained_in",
        "or": "logical_or",
        "and": "logical_and",
        "not": "logical_not",
        "match": "pattern_match",
        "define": "schema_define",
        "insert": "data_insert",
        "delete": "data_delete",
        "undefine": "schema_undefine",
    }

    def __init__(self):
        self._defined_attributes: set[str] = set()
        self._defined_entities: set[str] = set()
        self._defined_relations: set[str] = set()

    def _sanitize_name(self, name: str) -> str:
        """Replace reserved keywords with safe alternatives."""
        return self.RESERVED_KEYWORDS.get(name, name)

    def generate_initial_schema(self, analysis: AnalysisResult) -> str:
        """
        Generate complete initial schema from first scene analysis.

        Args:
            analysis: Analysis result from vision analyzer

        Returns:
            TypeQL define statement string
        """
        # Track what's in base schema
        self._defined_attributes = {
            "name", "color", "material", "shape", "size",
            "position_description", "scene_id"
        }
        self._defined_entities = {"physical_object"}
        self._defined_relations = {
            "spatial_relation", "on", "under", "next_to",
            "in_front_of", "behind", "inside", "contains"
        }

        # Start with base schema (without 'define' keyword yet)
        schema_parts = ["define"]
        schema_parts.append(BASE_SCHEMA.strip().replace("define\n  ", "  "))

        # Generate additional schema from analysis
        additional = self._generate_from_analysis(analysis, include_define=False)
        if additional:
            schema_parts.append("")
            schema_parts.append("  # Scene-specific types")
            schema_parts.append(additional)

        return "\n".join(schema_parts)

    def generate_schema_additions(self, analysis: AnalysisResult) -> str | None:
        """
        Generate schema additions for new scene (define statements only).

        Args:
            analysis: Analysis result with schema_changes

        Returns:
            TypeQL define statement string or None if no changes needed
        """
        if not analysis.schema_changes:
            return None

        return self._generate_from_analysis(analysis)

    def _generate_from_analysis(self, analysis: AnalysisResult, include_define: bool = True) -> str:
        """Generate TypeQL from analysis schema changes."""
        lines = ["define"] if include_define else []
        has_content = False

        # Process schema changes in order: attributes, entities, relations, modifications
        attr_changes = [c for c in analysis.schema_changes if c.change_type == "new_attribute_type"]
        entity_changes = [c for c in analysis.schema_changes if c.change_type == "new_entity_type"]
        relation_changes = [c for c in analysis.schema_changes if c.change_type == "new_relation_type"]
        mod_changes = [c for c in analysis.schema_changes if c.change_type == "modified_type"]

        # Generate attribute types
        for change in attr_changes:
            attr_def = self._generate_attribute_type(change.definition)
            if attr_def:
                lines.append(f"  {attr_def}")
                has_content = True

        # Generate entity types
        for change in entity_changes:
            entity_def = self._generate_entity_type(change.definition)
            if entity_def:
                lines.append(f"  {entity_def}")
                has_content = True

        # Generate relation types
        for change in relation_changes:
            relation_def = self._generate_relation_type(change.definition)
            if relation_def:
                lines.append(f"  {relation_def}")
                has_content = True

        # Generate modifications (add owns/plays to existing types)
        for change in mod_changes:
            mod_def = self._generate_type_modification(change.definition)
            if mod_def:
                lines.append(f"  {mod_def}")
                has_content = True

        # Also infer types from entities if no explicit schema changes
        if not has_content and (analysis.new_entities or analysis.pending_entities):
            inferred = self._infer_types_from_entities(
                analysis.new_entities + analysis.pending_entities
            )
            if inferred:
                lines.extend(f"  {line}" for line in inferred)
                has_content = True

        return "\n".join(lines) if has_content else ""

    def _generate_attribute_type(self, definition: dict) -> str | None:
        """Generate attribute type definition."""
        name = definition.get("name")
        if not name:
            return None

        # Sanitize name to avoid reserved keywords
        name = self._sanitize_name(name)

        if name in self._defined_attributes:
            return None

        value_type = definition.get("value_type", "string")
        value_type = self.VALUE_TYPE_MAP.get(value_type.lower(), "string")

        self._defined_attributes.add(name)
        return f"attribute {name} value {value_type};"

    def _generate_entity_type(self, definition: dict) -> str | None:
        """Generate entity type definition."""
        name = definition.get("name")
        if not name:
            return None

        # Sanitize name to avoid reserved keywords
        name = self._sanitize_name(name)

        if name in self._defined_entities:
            return None

        parent = definition.get("parent", "physical_object")
        # If parent is "entity", use physical_object instead
        if parent == "entity":
            parent = "physical_object"

        owns = definition.get("owns", [])
        plays = definition.get("plays", [])

        parts = [f"entity {name}"]

        # Always add parent (defaults to physical_object)
        if parent:
            parts.append(f"sub {parent}")

        # Attributes already owned by physical_object - don't redeclare
        inherited_owns = {"name", "color", "material", "shape", "size", "position_description", "scene_id"}

        for attr in owns:
            # Sanitize attribute names too
            attr = self._sanitize_name(attr)
            if attr not in self._defined_attributes:
                # Need to define this attribute first - skip for now
                continue
            # Skip attributes already owned by parent
            if attr in inherited_owns and parent == "physical_object":
                continue
            parts.append(f"owns {attr}")

        for role in plays:
            parts.append(f"plays {role}")

        self._defined_entities.add(name)

        if len(parts) == 1:
            return f"{parts[0]};"
        else:
            return f"{parts[0]},\n    " + ",\n    ".join(parts[1:]) + ";"

    def _generate_relation_type(self, definition: dict) -> str | None:
        """Generate relation type definition."""
        name = definition.get("name")
        if not name:
            return None

        # Sanitize name to avoid reserved keywords
        name = self._sanitize_name(name)

        if name in self._defined_relations:
            return None

        parent = definition.get("parent", "relation")
        roles = definition.get("roles", [])

        parts = [f"relation {name}"]

        if parent and parent != "relation":
            parts.append(f"sub {parent}")

        for role in roles:
            role_name = role.get("name") if isinstance(role, dict) else role
            parts.append(f"relates {role_name}")

        self._defined_relations.add(name)

        if len(parts) == 1:
            return f"{parts[0]};"
        else:
            return f"{parts[0]},\n    " + ",\n    ".join(parts[1:]) + ";"

    def _generate_type_modification(self, definition: dict) -> str | None:
        """Generate type modification (adding owns/plays)."""
        name = definition.get("name")
        if not name:
            return None

        add_owns = definition.get("add_owns", [])
        add_plays = definition.get("add_plays", [])

        parts = []

        for attr in add_owns:
            if attr in self._defined_attributes:
                parts.append(f"{name} owns {attr};")

        for role in add_plays:
            parts.append(f"{name} plays {role};")

        return "\n  ".join(parts) if parts else None

    def _infer_types_from_entities(self, entities: list) -> list[str]:
        """Infer entity types from extracted entities."""
        lines = []
        inferred_types = set()

        for entity in entities:
            entity_type = entity.type
            if entity_type in self._defined_entities or entity_type in inferred_types:
                continue

            # Create as subtype of physical_object
            lines.append(f"entity {entity_type} sub physical_object;")
            inferred_types.add(entity_type)
            self._defined_entities.add(entity_type)

        return lines

    def get_schema_summary(self) -> dict:
        """Get summary of defined schema elements."""
        return {
            "attributes": list(self._defined_attributes),
            "entities": list(self._defined_entities),
            "relations": list(self._defined_relations)
        }
