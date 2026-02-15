#!/bin/bash
set -e

# Step 1: Create a Python virtual environment in ./venv
python3 -m venv venv

# Step 2: Activate the virtual environment
source venv/bin/activate

# Step 3: Install all dependencies from requirements.txt
pip install -r requirements.txt

# Step 4: Run the application
python main.py