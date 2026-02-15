#!/bin/bash
set -e

# Create a Python virtual environment in ./venv
python -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Check if requirements.txt exists and install dependencies
if [ -f requirements.txt ]; then
    pip install -r requirements.txt
else
    echo "No requirements.txt file found. Skipping dependency installation."
fi

# Run the application
python main.py