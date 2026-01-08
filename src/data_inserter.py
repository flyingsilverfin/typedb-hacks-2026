"""Data inserter for populating TypeDB with extracted entities and relations."""

from dataclasses import dataclass, field
from typing import Any

from .typedb_client import TypeDBClient
from .vision_analyzer import AnalysisResult, EntityData, RelationData


@dataclass
class InsertResult:
    """Result of data insertion."""
    success: bool
    entities_inserted: int = 0
    relations_inserted: int = 0
    errors: list[str] = field(default_factory=list)


class DataInserter:
    """Insert extracted entities and relations into TypeDB."""

    def __init__(self, client: TypeDBClient):
        self.client = client

    def insert_analysis_result(
        self,
        analysis: AnalysisResult,
        scene_id: str | None = None
    ) -> InsertResult:
        """
        Insert all data from an analysis result.

        Args:
            analysis: Analysis result containing entities and relations
            scene_id: Optional scene identifier to tag all entities

        Returns:
            InsertResult with counts and any errors
        """
        result = InsertResult(success=True)

        # Combine new_entities and pending_entities (pending should now fit schema)
        all_entities = analysis.new_entities + analysis.pending_entities
        all_relations = analysis.new_relations + analysis.pending_relations

        # Insert entities first
        for entity in all_entities:
            try:
                self._insert_entity(entity, scene_id)
                result.entities_inserted += 1
            except Exception as e:
                result.errors.append(f"Failed to insert entity {entity.id}: {e}")

        # Then insert relations
        for relation in all_relations:
            try:
                self._insert_relation(relation)
                result.relations_inserted += 1
            except Exception as e:
                result.errors.append(f"Failed to insert relation {relation.type}: {e}")

        result.success = len(result.errors) == 0
        return result

    def _insert_entity(self, entity: EntityData, scene_id: str | None = None) -> None:
        """Insert a single entity."""
        # Build insert query
        parts = [f"$e isa {entity.type}"]

        # Add name attribute (using entity id as name)
        parts.append(f'has name "{self._escape_string(entity.id)}"')

        # Add scene_id if provided
        if scene_id:
            parts.append(f'has scene_id "{self._escape_string(scene_id)}"')

        # Add other attributes
        for attr_name, attr_value in entity.attributes.items():
            if attr_name in ("name", "scene_id"):
                continue  # Already handled

            formatted_value = self._format_attribute_value(attr_value)
            parts.append(f"has {attr_name} {formatted_value}")

        query = "insert\n  " + ",\n  ".join(parts) + ";"
        self.client.execute_write(query)

    def _insert_relation(self, relation: RelationData) -> None:
        """Insert a single relation."""
        # Look up entities by name
        from_var = "$from"
        to_var = "$to"

        # Build match clause to find entities
        match_parts = [
            f'{from_var} isa physical_object, has name "{self._escape_string(relation.from_entity)}"',
            f'{to_var} isa physical_object, has name "{self._escape_string(relation.to_entity)}"'
        ]

        # Determine role names based on relation type
        # Default to subject/reference for spatial relations
        from_role = relation.roles.get("from", "subject")
        to_role = relation.roles.get("to", "reference")

        # Build insert clause
        insert_part = f"({from_role}: {from_var}, {to_role}: {to_var}) isa {relation.type}"

        query = f"""match
  {match_parts[0]};
  {match_parts[1]};
insert
  {insert_part};"""

        self.client.execute_write(query)

    def _format_attribute_value(self, value: Any) -> str:
        """Format an attribute value for TypeQL."""
        if isinstance(value, str):
            return f'"{self._escape_string(value)}"'
        elif isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, (int, float)):
            return str(value)
        else:
            return f'"{self._escape_string(str(value))}"'

    def _escape_string(self, value: str) -> str:
        """Escape special characters in string values."""
        return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")

    def insert_entities_batch(
        self,
        entities: list[EntityData],
        scene_id: str | None = None
    ) -> InsertResult:
        """
        Insert multiple entities in a batch.

        Args:
            entities: List of entities to insert
            scene_id: Optional scene identifier

        Returns:
            InsertResult
        """
        result = InsertResult(success=True)

        for entity in entities:
            try:
                self._insert_entity(entity, scene_id)
                result.entities_inserted += 1
            except Exception as e:
                result.errors.append(f"Failed to insert entity {entity.id}: {e}")

        result.success = len(result.errors) == 0
        return result

    def insert_relations_batch(self, relations: list[RelationData]) -> InsertResult:
        """
        Insert multiple relations in a batch.

        Args:
            relations: List of relations to insert

        Returns:
            InsertResult
        """
        result = InsertResult(success=True)

        for relation in relations:
            try:
                self._insert_relation(relation)
                result.relations_inserted += 1
            except Exception as e:
                result.errors.append(f"Failed to insert relation {relation.type}: {e}")

        result.success = len(result.errors) == 0
        return result

    def delete_scene(self, scene_id: str) -> int:
        """
        Delete all entities and relations for a scene.

        Args:
            scene_id: Scene identifier to delete

        Returns:
            Number of entities deleted
        """
        # First delete relations involving scene entities
        delete_relations = f"""
match
  $e isa physical_object, has scene_id "{self._escape_string(scene_id)}";
  $r ($e) isa relation;
delete
  $r isa relation;
"""
        try:
            self.client.execute_write(delete_relations)
        except Exception:
            pass  # May not have relations

        # Then delete entities
        delete_entities = f"""
match
  $e isa physical_object, has scene_id "{self._escape_string(scene_id)}";
delete
  $e isa physical_object;
"""
        try:
            self.client.execute_write(delete_entities)
        except Exception:
            pass

        return 0  # TypeDB doesn't return count easily
