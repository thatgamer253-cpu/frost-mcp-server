#!/bin/bash

# This script installs the necessary system dependencies for the Crypto Portfolio Dashboard application.

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Update package lists
if command_exists apt; then
    sudo apt update
elif command_exists dnf; then
    sudo dnf check-update
else
    echo "Neither apt nor dnf package manager found. Exiting."
    exit 1
fi

# Install dependencies
install_dependencies() {
    if command_exists apt; then
        sudo apt install -y python3 python3-pip python3-venv libnotify-bin
    elif command_exists dnf; then
        sudo dnf install -y python3 python3-pip python3-virtualenv libnotify
    else
        echo "Neither apt nor dnf package manager found. Exiting."
        exit 1
    fi
}

# Install Python packages
install_python_packages() {
    python3 -m pip install --upgrade pip
    python3 -m pip install -r requirements.txt
}

# Execute installation functions
install_dependencies
install_python_packages

echo "Installation completed successfully."