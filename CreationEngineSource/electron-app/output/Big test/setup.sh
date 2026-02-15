#!/bin/bash
set -e

# Create a Python virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Create a requirements.txt file with the dependencies
cat <<EOL > requirements.txt
aiohttp
fastapi
state_manager
PyYAML
pysqlite3
task_manager
asyncio
error_handler
plugin_loader
EOL

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py