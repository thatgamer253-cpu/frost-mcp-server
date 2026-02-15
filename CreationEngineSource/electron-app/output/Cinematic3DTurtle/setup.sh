{ echo "Failed to create virtual environment"; exit 1; }

# Activate virtual environment
source ./venv/bin/activate || { echo "Failed to activate virtual environment"; exit 1; }

# Install dependencies from requirements.txt
pip install -r requirements.txt || { echo "Failed to install dependencies"; exit 1; }