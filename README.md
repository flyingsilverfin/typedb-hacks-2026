# typedb-hacks-2026
TypeDB 2026 hackathon

## Setup

### System Dependencies
```bash
apt-get update && apt-get install ffmpeg libsm6 libxext6 -y
```

### Python Environment
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### TypeDB Server
Extract and start the TypeDB server with development mode:
```bash
tar -xzf typedb-all-linux-arm64-3.7.2.tar.gz
./typedb-all-linux-arm64-3.7.2/typedb server --development-mode.enabled=true
```

### Environment Variables
```bash
export ANTHROPIC_API_KEY=your_api_key_here
```

## Usage

### Full Pipeline (load to database)
```bash
source venv/bin/activate
python3 main.py load /path/to/video.mp4 -y
```

### Query the scene
```bash
python3 main.py query "What objects are in the room?"
python3 main.py query "How many monitors are there?"
python3 main.py query "What black objects are there?"
```

### Debugging Commands

For debugging, the pipeline can be run in stages:

```bash
# 1. Extract and analyze only (no database interaction)
python3 main.py extract video.mp4

# Save analysis to JSON file
python3 main.py extract video.mp4 -o analysis.json

# 2. Preview schema and TypeQL queries (read-only database check)
python3 main.py preview video.mp4

# 3. Full pipeline - load into database
python3 main.py load video.mp4 -y

# 4. Query existing database
python3 main.py query "What is in the scene?"
```

### Other Commands

```bash
# Show database schema
python3 main.py schema

# Show database info
python3 main.py info

# Execute raw TypeQL
python3 main.py execute "match \$obj isa physical_object, has name \$n; fetch { \"name\": \$n };"

# Clear database
python3 main.py clear -y
```
