#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "🚀 Starting Render Build Process..."

# Use python3 explicitely
PYTHON_BIN="python3.12"
if ! command -v $PYTHON_BIN &> /dev/null; then
    echo "⚠️  python3.12 not found, falling back to python3"
    PYTHON_BIN="python3"
fi

echo "🔍 Using Python: $($PYTHON_BIN --version) at $(which $PYTHON_BIN)"

# Create a virtual environment to isolate dependencies
# Render persists /opt/render/project/src, so we can store venv there
if [ ! -d "venv" ]; then
  echo "📦 Creating virtual environment..."
  $PYTHON_BIN -m venv venv
else
  echo "♻️  Using existing virtual environment..."
fi

# Activate venv
source venv/bin/activate

# Upgrade pip and build tools
echo "⬆️  Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install dependencies
echo "📥 Installing dependencies from requirements.txt..."
pip install -r requirements.txt

# Verify installation of critical package
echo "🕵️  Verifying installation..."
python -c "import mcp; print('✅ MCP module found at:', mcp.__file__)" || { echo "❌ MCP module NOT found!"; exit 1; }

echo "✅ Build completed successfully!"
