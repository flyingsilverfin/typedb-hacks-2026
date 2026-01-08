# Claude.md - Project Notes

## Project Overview
Scene understanding system that extracts entities and relations from video using Claude's vision API and stores them in TypeDB for natural language querying.

## Quick Start
```bash
# Activate virtual environment
source venv/bin/activate

# Set API key
export ANTHROPIC_API_KEY=your_key

# Start TypeDB server with development mode
./typedb-all-linux-arm64-3.7.2/typedb server --development-mode.enabled=true

# Full pipeline (extract + analyze + load to DB)
python3 main.py load /opt/project/room_video_1.mp4 -y

# Query the scene
python3 main.py query "What objects are in the room?"
```

## Debugging Commands

For debugging purposes, the pipeline can be run in stages:

```bash
# 1. Extract frames and analyze (no DB interaction)
python3 main.py extract video.mp4 -o analysis.json

# 2. Preview TypeQL queries that would be generated
python3 main.py preview video.mp4

# 3. Full pipeline - load everything into database
python3 main.py load video.mp4 -y

# 4. Query existing database
python3 main.py query "What black objects are there?"
```

## Architecture
- `src/video_processor.py` - Frame extraction from video (OpenCV)
- `src/vision_analyzer.py` - Claude vision API for entity/relation extraction
- `src/schema_generator.py` - Generate TypeDB schema from analysis
- `src/schema_migrator.py` - Handle schema evolution
- `src/data_inserter.py` - Insert entities/relations into TypeDB
- `src/query_translator.py` - Natural language to TypeQL translation
- `src/typedb_client.py` - TypeDB connection wrapper

## Test Status

### Frame Extraction
- **Status**: Working
- **Test**: Extracted 3 frames from `/opt/project/room_video_1.mp4`
- **Video info**: 768x1024, 21.8 fps, 6.5 seconds, 141 frames

### Entity Resolution (Vision Analysis)
- **Status**: Working
- **Model**: claude-sonnet-4-20250514
- **Detected from room_video_1.mp4**:
  - 21 entities: 2 people, 1 desk, 2 chairs, 3 monitors, 2 laptops, 2 light fixtures, 1 wall, 1 computer tower, 2 keyboards, 1 mouse, 1 book, 1 cable, 1 door, 1 office_space
  - 14 entity types proposed (person, desk, computer_monitor, laptop, chair, etc.)
  - 5 attribute types (name, color, material, size, position_description)
  - 5 relation types (sitting_on, on, under, attached_to, in)

### TypeDB Integration
- **Status**: Working
- **Server**: `./typedb-all-linux-arm64-3.7.2/typedb server`
- **Test**: Full pipeline run successfully
  - 23 entities inserted into database
  - Schema generated and applied automatically
  - Natural language queries working

## Dependencies
Using Python 3.12 with venv at `./venv/`
- opencv-python-headless (for ARM/headless environments)
- anthropic
- typedb-driver
- click

## Notes
- Using `opencv-python-headless` instead of `opencv-python` to avoid libGL dependency
- TypeDB 3.x syntax differs from 2.x - see `plan.md` for reference
- System dependencies required: `apt-get install ffmpeg libsm6 libxext6 -y` (documented in README.md)
- TypeDB server running in development mode for easier testing and debugging

## Command Reference

### Main Commands (Require ANTHROPIC_API_KEY)
- `extract <video>` - Extract frames and analyze with vision (no DB)
  - Options: `--fps`, `--max-frames`, `-o/--output` (save to JSON)
  - **Requires API key** for vision analysis
- `preview <video>` - Show schema and TypeQL queries (read-only DB check)
  - Shows full schema that would be created
  - Shows all insert queries that would be executed
  - **Requires API key** for vision analysis
- `load <video>` - Full pipeline: extract, analyze, and load to database
  - Options: `--fps`, `--max-frames`, `--scene-id`, `-y/--yes`
  - **Requires API key** for vision analysis
- `query <question>` - Natural language query on existing database
  - Always shows generated TypeQL query before executing
  - **Requires API key** for NL→TypeQL translation

### Utility Commands (No API Key Required)
- `schema` - Show current database schema
- `info` - Show database connection info
- `execute <typeql>` - Execute raw TypeQL query (no API key needed)
- `clear` - Delete and recreate database
- `analyze` - Alias for `load` (backward compatibility)

## Session Log

### 2026-01-08: Full pipeline testing completed
- Frame extraction: PASS - extracted 2 frames from video
- Entity resolution: PASS - detected 21 entities with attributes and proposed schema
- Schema generation: PASS - auto-generated TypeDB schema with entity/relation/attribute types
- Data insertion: PASS - inserted 23 entities into TypeDB
- Natural language queries: PASS - successfully queried entities by type, color, and other attributes
- Fixes applied:
  - Removed `@key` annotation (not supported in TypeDB 3.x)
  - Added reserved keyword sanitization (`in` → `contained_in`)
  - Fixed entity inheritance to use `physical_object` as parent
  - Removed duplicate `owns` clauses from inherited attributes
  - Fixed TypeQL fetch syntax to avoid `type()` function

### 2026-01-08: Project cleanup
- Added comprehensive .gitignore file
  - Ignores: venv, __pycache__, *.log, bin/, .DS_Store, IDE files
  - Ignores: TypeDB artifacts, tar.gz files, output files
- Removed __pycache__ files from git tracking

### 2026-01-08: Query validation and improvements
- Improved TypeQL query generation prompt with explicit syntax rules
- Added validation to detect malformed queries (missing variables)
- Better error messages when query generation fails
- Invalid queries are caught before being sent to database

### 2026-01-08: Debugging commands added
- Created staged pipeline commands for better debugging:
  - `extract` - Frame extraction + vision analysis only (no DB)
  - `preview` - Shows full schema and all TypeQL insert queries
  - `load` - Full pipeline (renamed from `analyze`)
  - `query` - Natural language queries (already existed)
- Added JSON export option to `extract` command (`-o/--output`)
- Added `analyze` as backward compatibility alias for `load`
- Updated `query` and `execute` commands to always show TypeQL before/during execution
- TypeQL is now shown even when errors occur (query preserved on error)
- Removed `--raw` flag from `query` (no longer needed)
- **Made API key optional**: Only required for commands that use Claude API
  - Commands requiring API key: `extract`, `preview`, `load`, `query`
  - Commands without API key: `schema`, `info`, `execute`, `clear`
  - Lazy initialization prevents unnecessary API key checks
- Updated documentation in README.md and Claude.md
- TypeDB server configured with `--development-mode.enabled=true`
