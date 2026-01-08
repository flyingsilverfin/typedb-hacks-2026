#!/usr/bin/env python3
"""
Scene Graph CLI - Extract entities and relations from video using Claude vision
and store them in TypeDB for natural language querying.
"""

import json
import sys
import uuid
from pathlib import Path

import click

from src.typedb_client import TypeDBClient, TypeDBConfig
from src.video_processor import VideoProcessor
from src.vision_analyzer import VisionAnalyzer
from src.schema_generator import SchemaGenerator
from src.schema_migrator import SchemaMigrator
from src.data_inserter import DataInserter
from src.query_translator import QueryTranslator


@click.group()
@click.option("--db-address", default="localhost:1729", help="TypeDB server address")
@click.option("--db-name", default="scene_graph", help="Database name")
@click.option("--db-user", default="admin", help="Database username")
@click.option("--db-password", default="password", help="Database password")
@click.pass_context
def cli(ctx, db_address, db_name, db_user, db_password):
    """Scene Graph - Visual Scene Understanding with TypeDB"""
    ctx.ensure_object(dict)
    ctx.obj["config"] = TypeDBConfig(
        address=db_address,
        database=db_name,
        username=db_user,
        password=db_password
    )


@cli.command()
@click.argument("video_path", type=click.Path(exists=True))
@click.option("--fps", default=0.5, help="Frames to extract per second")
@click.option("--max-frames", default=5, help="Maximum frames to extract")
@click.option("--scene-id", default=None, help="Scene identifier (auto-generated if not provided)")
@click.option("--yes", "-y", is_flag=True, help="Auto-confirm schema changes")
@click.pass_context
def analyze(ctx, video_path, fps, max_frames, scene_id, yes):
    """Analyze a video and populate the database with extracted entities."""
    config = ctx.obj["config"]
    scene_id = scene_id or f"scene_{uuid.uuid4().hex[:8]}"

    click.echo(f"Analyzing video: {video_path}")
    click.echo(f"Scene ID: {scene_id}")

    # Extract frames
    click.echo(f"\nExtracting frames ({fps} fps, max {max_frames})...")
    processor = VideoProcessor(frames_per_second=fps, max_frames=max_frames)

    try:
        frames = processor.extract_frames(video_path)
        click.echo(f"Extracted {len(frames)} frames")
    except Exception as e:
        click.echo(f"Error extracting frames: {e}", err=True)
        sys.exit(1)

    if not frames:
        click.echo("No frames extracted from video", err=True)
        sys.exit(1)

    # Connect to TypeDB
    click.echo("\nConnecting to TypeDB...")
    with TypeDBClient(config) as client:
        is_new_db = client.ensure_database()

        if is_new_db:
            click.echo(f"Created new database: {config.database}")
        else:
            click.echo(f"Using existing database: {config.database}")

        # Get current schema
        current_schema = client.get_schema()
        has_schema = current_schema is not None

        # Analyze with Claude
        click.echo("\nAnalyzing frames with Claude...")
        analyzer = VisionAnalyzer()
        analysis = analyzer.analyze_frames(frames, current_schema)

        if analysis.raw_response and "error" in analysis.raw_response:
            click.echo(f"Analysis error: {analysis.raw_response}", err=True)
            sys.exit(1)

        # Report findings
        total_entities = len(analysis.new_entities) + len(analysis.pending_entities)
        total_relations = len(analysis.new_relations) + len(analysis.pending_relations)
        schema_changes = len(analysis.schema_changes)

        click.echo(f"\nAnalysis complete:")
        click.echo(f"  - {len(analysis.new_entities)} entities fit existing schema")
        click.echo(f"  - {len(analysis.pending_entities)} entities require schema changes")
        click.echo(f"  - {total_relations} relations identified")
        click.echo(f"  - {schema_changes} schema changes proposed")

        # Handle schema
        if not has_schema:
            # First scene - create initial schema
            click.echo("\nGenerating initial schema...")
            generator = SchemaGenerator()
            schema_typeql = generator.generate_initial_schema(analysis)

            click.echo("\nInitial schema:")
            click.echo(schema_typeql[:500] + "..." if len(schema_typeql) > 500 else schema_typeql)

            if not yes:
                if not click.confirm("\nApply initial schema?"):
                    click.echo("Aborted.")
                    sys.exit(0)

            try:
                client.execute_schema(schema_typeql)
                click.echo("Schema applied successfully")
            except Exception as e:
                click.echo(f"Error applying schema: {e}", err=True)
                sys.exit(1)

        elif schema_changes > 0:
            # Existing schema - plan migration
            click.echo("\nPlanning schema migration...")
            migrator = SchemaMigrator(client)
            plan = migrator.plan_migration(analysis)

            if plan.has_changes:
                click.echo(f"\n{plan.summary()}")

                if not yes:
                    if not click.confirm("\nProceed with migration?"):
                        click.echo("Aborted.")
                        sys.exit(0)

                click.echo("\nExecuting migration...")
                result = migrator.execute_migration(plan)

                if result.success:
                    click.echo(f"Migration complete: {len(result.executed_operations)} operations")
                else:
                    click.echo(f"Migration failed at: {result.failed_operation.description}", err=True)
                    click.echo(f"Error: {result.error}", err=True)
                    sys.exit(1)

        # Insert data
        click.echo("\nInserting data...")
        inserter = DataInserter(client)
        insert_result = inserter.insert_analysis_result(analysis, scene_id)

        click.echo(f"Inserted {insert_result.entities_inserted} entities")
        click.echo(f"Inserted {insert_result.relations_inserted} relations")

        if insert_result.errors:
            click.echo(f"\nWarnings ({len(insert_result.errors)}):")
            for error in insert_result.errors[:5]:
                click.echo(f"  - {error}")

        click.echo(f"\nDone! Scene '{scene_id}' added to database.")


@cli.command()
@click.argument("question")
@click.option("--raw", is_flag=True, help="Show raw TypeQL query")
@click.pass_context
def query(ctx, question, raw):
    """Ask a natural language question about the scene."""
    config = ctx.obj["config"]

    with TypeDBClient(config) as client:
        if not client.database_exists():
            click.echo(f"Database '{config.database}' does not exist. Run 'analyze' first.", err=True)
            sys.exit(1)

        translator = QueryTranslator(client)
        result = translator.query(question)

        if raw or not result.success:
            click.echo(f"TypeQL: {result.typeql}\n")

        if not result.success:
            click.echo(f"Error: {result.error}", err=True)
            sys.exit(1)

        if not result.results:
            click.echo("No results found.")
            return

        click.echo(f"Found {len(result.results)} results:\n")
        for i, doc in enumerate(result.results, 1):
            click.echo(f"{i}. {json.dumps(doc, indent=2)}")


@cli.command()
@click.argument("typeql")
@click.pass_context
def execute(ctx, typeql):
    """Execute a raw TypeQL query."""
    config = ctx.obj["config"]

    with TypeDBClient(config) as client:
        if not client.database_exists():
            click.echo(f"Database '{config.database}' does not exist.", err=True)
            sys.exit(1)

        translator = QueryTranslator(client)
        result = translator.execute_typeql(typeql)

        if not result.success:
            click.echo(f"Error: {result.error}", err=True)
            sys.exit(1)

        if not result.results:
            click.echo("Query executed. No results returned.")
            return

        click.echo(f"Results ({len(result.results)}):\n")
        for i, doc in enumerate(result.results, 1):
            click.echo(f"{i}. {json.dumps(doc, indent=2)}")


@cli.command()
@click.pass_context
def schema(ctx):
    """Show the current database schema."""
    config = ctx.obj["config"]

    with TypeDBClient(config) as client:
        if not client.database_exists():
            click.echo(f"Database '{config.database}' does not exist.", err=True)
            sys.exit(1)

        current_schema = client.get_schema()

        if current_schema:
            click.echo(current_schema)
        else:
            click.echo("No schema defined yet.")


@cli.command()
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
@click.pass_context
def clear(ctx, yes):
    """Clear the database (delete and recreate)."""
    config = ctx.obj["config"]

    if not yes:
        if not click.confirm(f"Delete database '{config.database}'? This cannot be undone."):
            click.echo("Aborted.")
            return

    with TypeDBClient(config) as client:
        if client.delete_database():
            click.echo(f"Database '{config.database}' deleted.")
        else:
            click.echo(f"Database '{config.database}' did not exist.")


@cli.command()
@click.pass_context
def info(ctx):
    """Show database information."""
    config = ctx.obj["config"]

    click.echo(f"TypeDB Address: {config.address}")
    click.echo(f"Database: {config.database}")

    try:
        with TypeDBClient(config) as client:
            if client.database_exists():
                click.echo("Status: Connected")

                # Try to get some stats
                try:
                    result = client.execute_read(
                        "match $e isa physical_object; fetch { 'count': count };"
                    )
                    click.echo(f"Entities: {result}")
                except Exception:
                    click.echo("Entities: (unable to count)")
            else:
                click.echo("Status: Database does not exist")
    except Exception as e:
        click.echo(f"Status: Connection failed - {e}")


if __name__ == "__main__":
    cli()
