"""Schema migrator for handling TypeDB schema evolution."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .typedb_client import TypeDBClient
from .vision_analyzer import AnalysisResult, SchemaChange


class OperationType(Enum):
    """Types of schema operations."""
    DEFINE = "define"
    REDEFINE = "redefine"
    UNDEFINE = "undefine"


@dataclass
class SchemaOperation:
    """A single schema operation to execute."""
    operation: OperationType
    typeql: str
    description: str
    requires_data_migration: bool = False
    migration_queries: list[str] = field(default_factory=list)


@dataclass
class MigrationPlan:
    """Complete migration plan with ordered operations."""
    operations: list[SchemaOperation] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return len(self.operations) > 0

    def summary(self) -> str:
        """Get human-readable summary of the migration plan."""
        if not self.operations:
            return "No schema changes required."

        lines = [f"Migration plan with {len(self.operations)} operations:"]
        for i, op in enumerate(self.operations, 1):
            lines.append(f"  {i}. [{op.operation.value.upper()}] {op.description}")
            if op.requires_data_migration:
                lines.append(f"      (requires data migration)")

        if self.warnings:
            lines.append("\nWarnings:")
            for warning in self.warnings:
                lines.append(f"  - {warning}")

        return "\n".join(lines)


@dataclass
class MigrationResult:
    """Result of executing a migration."""
    success: bool
    executed_operations: list[SchemaOperation] = field(default_factory=list)
    failed_operation: SchemaOperation | None = None
    error: str | None = None


class SchemaMigrator:
    """Handle schema evolution and migrations for TypeDB."""

    # Value type mapping
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

    def __init__(self, client: TypeDBClient):
        self.client = client

    def plan_migration(self, analysis: AnalysisResult) -> MigrationPlan:
        """
        Create a migration plan from analysis results.

        Operations are ordered by dependency:
        1. New attribute types (must exist before entities can own them)
        2. New entity types
        3. New relation types
        4. Type modifications (add owns/plays)
        5. Redefine operations (if any)

        Args:
            analysis: Analysis result with schema_changes

        Returns:
            MigrationPlan with ordered operations
        """
        plan = MigrationPlan()

        if not analysis.schema_changes:
            return plan

        # Group changes by type
        attr_changes = []
        entity_changes = []
        relation_changes = []
        mod_changes = []

        for change in analysis.schema_changes:
            if change.change_type == "new_attribute_type":
                attr_changes.append(change)
            elif change.change_type == "new_entity_type":
                entity_changes.append(change)
            elif change.change_type == "new_relation_type":
                relation_changes.append(change)
            elif change.change_type == "modified_type":
                mod_changes.append(change)

        # 1. Generate attribute type definitions
        for change in attr_changes:
            op = self._create_attribute_operation(change)
            if op:
                plan.operations.append(op)

        # 2. Generate entity type definitions
        for change in entity_changes:
            op = self._create_entity_operation(change)
            if op:
                plan.operations.append(op)

        # 3. Generate relation type definitions
        for change in relation_changes:
            op = self._create_relation_operation(change)
            if op:
                plan.operations.append(op)

        # 4. Generate type modifications
        for change in mod_changes:
            ops = self._create_modification_operations(change)
            plan.operations.extend(ops)

        return plan

    def _create_attribute_operation(self, change: SchemaChange) -> SchemaOperation | None:
        """Create operation for new attribute type."""
        defn = change.definition
        name = defn.get("name")
        if not name:
            return None

        value_type = defn.get("value_type", "string")
        value_type = self.VALUE_TYPE_MAP.get(value_type.lower(), "string")

        typeql = f"define attribute {name} value {value_type};"

        return SchemaOperation(
            operation=OperationType.DEFINE,
            typeql=typeql,
            description=f"New attribute type: {name} ({value_type})"
        )

    def _create_entity_operation(self, change: SchemaChange) -> SchemaOperation | None:
        """Create operation for new entity type."""
        defn = change.definition
        name = defn.get("name")
        if not name:
            return None

        parent = defn.get("parent", "physical_object")
        owns = defn.get("owns", [])
        plays = defn.get("plays", [])

        # Attributes already owned by physical_object - don't redeclare
        inherited_owns = {"name", "color", "material", "shape", "size", "position_description", "scene_id"}

        parts = [f"entity {name}"]

        if parent and parent not in ("entity", "thing"):
            parts.append(f"sub {parent}")

        for attr in owns:
            # Skip attributes already owned by parent
            if attr in inherited_owns and parent == "physical_object":
                continue
            parts.append(f"owns {attr}")

        for role in plays:
            parts.append(f"plays {role}")

        if len(parts) == 1:
            typeql = f"define {parts[0]};"
        else:
            typeql = f"define {parts[0]},\n  " + ",\n  ".join(parts[1:]) + ";"

        return SchemaOperation(
            operation=OperationType.DEFINE,
            typeql=typeql,
            description=f"New entity type: {name}" + (f" (sub {parent})" if parent else "")
        )

    def _create_relation_operation(self, change: SchemaChange) -> SchemaOperation | None:
        """Create operation for new relation type."""
        defn = change.definition
        name = defn.get("name")
        if not name:
            return None

        parent = defn.get("parent")
        roles = defn.get("roles", [])

        parts = [f"relation {name}"]

        if parent and parent not in ("relation",):
            parts.append(f"sub {parent}")

        for role in roles:
            role_name = role.get("name") if isinstance(role, dict) else role
            parts.append(f"relates {role_name}")

        if len(parts) == 1:
            typeql = f"define {parts[0]};"
        else:
            typeql = f"define {parts[0]},\n  " + ",\n  ".join(parts[1:]) + ";"

        # Also add role players if specified
        player_lines = []
        for role in roles:
            if isinstance(role, dict) and "players" in role:
                role_name = role["name"]
                for player in role["players"]:
                    player_lines.append(f"  {player} plays {name}:{role_name};")

        if player_lines:
            typeql += "\n" + "\n".join(player_lines)

        return SchemaOperation(
            operation=OperationType.DEFINE,
            typeql=typeql,
            description=f"New relation type: {name}"
        )

    def _create_modification_operations(self, change: SchemaChange) -> list[SchemaOperation]:
        """Create operations for type modifications (adding owns/plays)."""
        operations = []
        defn = change.definition
        name = defn.get("name")
        if not name:
            return operations

        add_owns = defn.get("add_owns", [])
        add_plays = defn.get("add_plays", [])

        # Attributes owned by physical_object (inherited by all subtypes)
        # Don't redeclare these without specialization
        inherited_owns = {"name", "color", "material", "shape", "size", "position_description", "scene_id"}

        # Each owns/plays addition is a separate define statement
        for attr in add_owns:
            # Skip if this attribute is inherited from physical_object
            if attr in inherited_owns:
                continue
            typeql = f"define {name} owns {attr};"
            operations.append(SchemaOperation(
                operation=OperationType.DEFINE,
                typeql=typeql,
                description=f"{name} owns {attr} (additive)"
            ))

        for role in add_plays:
            typeql = f"define {name} plays {role};"
            operations.append(SchemaOperation(
                operation=OperationType.DEFINE,
                typeql=typeql,
                description=f"{name} plays {role} (additive)"
            ))

        return operations

    def execute_migration(self, plan: MigrationPlan) -> MigrationResult:
        """
        Execute a migration plan.

        Args:
            plan: Migration plan to execute

        Returns:
            MigrationResult indicating success/failure
        """
        result = MigrationResult(success=True)

        for operation in plan.operations:
            try:
                self.client.execute_schema(operation.typeql)
                result.executed_operations.append(operation)

                # Execute data migration if needed
                if operation.requires_data_migration:
                    for migration_query in operation.migration_queries:
                        self.client.execute_write(migration_query)

            except Exception as e:
                result.success = False
                result.failed_operation = operation
                result.error = str(e)
                break

        return result

    def execute_single_operation(self, operation: SchemaOperation) -> bool:
        """Execute a single schema operation."""
        try:
            self.client.execute_schema(operation.typeql)
            return True
        except Exception:
            return False
