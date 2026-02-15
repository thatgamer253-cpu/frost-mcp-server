#!/bin/bash
set -e

# Create a Python virtual environment in ./venv
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install all dependencies from requirements.txt
pip install -r requirements.txt

# Run the application
python3 main.py