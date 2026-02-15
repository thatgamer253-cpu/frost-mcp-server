#!/bin/bash
# install.sh - Script to install system dependencies via apt/dnf.

set -e

# Detect package manager and set variables accordingly.
if command -v apt-get &> /dev/null; then
    PKG_MANAGER="apt-get"
elif command -v dnf &> /dev/null; then
    PKG_MANAGER="dnf"
else
    echo "Unsupported system: Package manager not found."
    exit 1
fi

# Update package lists and install dependencies.
if [ "$PKG_MANAGER" == "apt-get" ]; then
    sudo apt-get update && sudo apt-get upgrade -y
    sudo apt-get install python3-pip python3-venv sqlite3 -y
elif [ "$PKG_MANAGER" == "dnf" ]; then
    sudo dnf check-update && sudo dnf upgrade -y
    sudo dnf install python3-pip python3-virtualenv sqlite -y
fi

# Install Python packages from requirements.txt.
pip install --upgrade pip
pip install -r requirements.txt

echo "Dependencies installed successfully."
exit 0