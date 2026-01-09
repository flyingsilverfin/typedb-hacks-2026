"""TypeDB client wrapper for scene graph database operations."""

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from typedb.driver import TypeDB, Credentials, DriverOptions, TransactionType


@dataclass
class TypeDBConfig:
    """Configuration for TypeDB connection."""
    address: str = "localhost:1729"
    username: str = "admin"
    password: str = "password"
    database: str = "scene_graph"
    tls_enabled: bool = False
    tls_root_ca: str | None = None


class TypeDBClient:
    """Wrapper for TypeDB database operations using TypeDB 3.x API."""

    def __init__(self, config: TypeDBConfig | None = None, debug: bool = False):
        self.config = config or TypeDBConfig()
        self.debug = debug
        self._driver = None

    def connect(self):
        """Establish connection to TypeDB server."""
        credentials = Credentials(self.config.username, self.config.password)
        options = DriverOptions(
            is_tls_enabled=self.config.tls_enabled,
            tls_root_ca_path=self.config.tls_root_ca
        )
        self._driver = TypeDB.driver(self.config.address, credentials, options)
        return self

    def close(self):
        """Close the database connection."""
        if self._driver:
            self._driver.close()
            self._driver = None

    def __enter__(self):
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @property
    def driver(self):
        if not self._driver:
            raise RuntimeError("Not connected. Call connect() first or use context manager.")
        return self._driver

    def ensure_database(self):
        """Create database if it doesn't exist."""
        databases = self.driver.databases
        if not databases.contains(self.config.database):
            databases.create(self.config.database)
            return True
        return False

    def delete_database(self):
        """Delete the database if it exists."""
        databases = self.driver.databases
        if databases.contains(self.config.database):
            databases.get(self.config.database).delete()
            return True
        return False

    def database_exists(self) -> bool:
        """Check if the database exists."""
        return self.driver.databases.contains(self.config.database)

    @contextmanager
    def schema_transaction(self):
        """Context manager for schema transactions."""
        with self.driver.transaction(
            self.config.database, TransactionType.SCHEMA
        ) as tx:
            yield tx

    @contextmanager
    def write_transaction(self):
        """Context manager for write transactions."""
        with self.driver.transaction(
            self.config.database, TransactionType.WRITE
        ) as tx:
            yield tx

    @contextmanager
    def read_transaction(self):
        """Context manager for read transactions."""
        with self.driver.transaction(
            self.config.database, TransactionType.READ
        ) as tx:
            yield tx

    def execute_schema(self, typeql: str) -> None:
        """Execute a schema query (define/redefine/undefine)."""
        if self.debug:
            print("\n" + "="*80)
            print("DEBUG: TYPEDB CLIENT - EXECUTE SCHEMA")
            print("="*80)
            print("TypeQL query:")
            print(typeql)
            print("="*80 + "\n")

        with self.schema_transaction() as tx:
            tx.query(typeql).resolve()
            tx.commit()

        if self.debug:
            print("DEBUG: Schema query executed successfully\n")

    def execute_write(self, typeql: str) -> list[dict]:
        """Execute a write query (insert/update/delete)."""
        if self.debug:
            print("\n" + "="*80)
            print("DEBUG: TYPEDB CLIENT - EXECUTE WRITE")
            print("="*80)
            print("TypeQL query:")
            print(typeql)
            print("="*80 + "\n")

        with self.write_transaction() as tx:
            result = tx.query(typeql).resolve()
            # Collect results before commit
            docs = []
            # Insert queries return concept rows, not documents
            if hasattr(result, '__iter__'):
                try:
                    for row in result:
                        docs.append(row)
                except Exception:
                    pass  # Some queries don't return rows
            tx.commit()

            if self.debug:
                print(f"DEBUG: Write query executed successfully ({len(docs)} results)\n")

            return docs

    def execute_read(self, typeql: str) -> list[dict]:
        """Execute a read query (match + fetch)."""
        if self.debug:
            print("\n" + "="*80)
            print("DEBUG: TYPEDB CLIENT - EXECUTE READ")
            print("="*80)
            print("TypeQL query:")
            print(typeql)
            print("="*80 + "\n")

        with self.read_transaction() as tx:
            result = tx.query(typeql).resolve()
            docs = []
            if hasattr(result, 'as_concept_documents'):
                for doc in result.as_concept_documents():
                    docs.append(doc)

            if self.debug:
                print(f"DEBUG: Read query executed successfully ({len(docs)} results)")
                if docs:
                    print("\nFirst few results:")
                    for i, doc in enumerate(docs[:3], 1):
                        print(f"  {i}. {doc}")
                print()

            return docs

    def get_schema(self) -> str | None:
        """Retrieve the current schema as TypeQL string.

        Returns None if database doesn't exist or has no schema.
        """
        if not self.database_exists():
            return None

        # Query all types and build schema representation
        schema_parts = []

        # Get attribute types
        attr_query = """
            match $t sub attribute;
            fetch {
                "label": $t,
                "value_type": $t
            };
        """

        # Get entity types
        entity_query = """
            match $t sub entity;
            fetch {
                "label": $t
            };
        """

        # Get relation types
        relation_query = """
            match $t sub relation;
            fetch {
                "label": $t
            };
        """

        try:
            with self.read_transaction() as tx:
                # For now, return a simplified schema representation
                # A full implementation would introspect all types, ownerships, and roles
                result = tx.query("match $t sub entity; fetch { 'type': $t };").resolve()
                entities = [doc for doc in result.as_concept_documents()]

                result = tx.query("match $t sub relation; fetch { 'type': $t };").resolve()
                relations = [doc for doc in result.as_concept_documents()]

                result = tx.query("match $t sub attribute; fetch { 'type': $t };").resolve()
                attributes = [doc for doc in result.as_concept_documents()]

            if not entities and not relations and not attributes:
                return None

            # Build a readable schema summary
            lines = ["# Current Schema", ""]

            if attributes:
                lines.append("## Attributes")
                for attr in attributes:
                    lines.append(f"- {attr}")
                lines.append("")

            if entities:
                lines.append("## Entities")
                for ent in entities:
                    lines.append(f"- {ent}")
                lines.append("")

            if relations:
                lines.append("## Relations")
                for rel in relations:
                    lines.append(f"- {rel}")

            return "\n".join(lines)

        except Exception as e:
            # Database might be empty or have no schema
            return None

    def get_schema_typeql(self) -> str | None:
        """Get the schema in TypeQL define format for LLM context."""
        if not self.database_exists():
            return None

        # This would ideally use TypeDB's schema export functionality
        # For now, we'll build it from queries
        try:
            schema_lines = ["define"]

            with self.read_transaction() as tx:
                # Query attribute types with value types
                # Query entity types with owns/plays
                # Query relation types with relates/owns
                # This is a simplified version - full implementation would be more comprehensive
                pass

            return "\n".join(schema_lines) if len(schema_lines) > 1 else None

        except Exception:
            return None
