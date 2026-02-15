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

# Install system dependencies
install_dependencies() {
    if command_exists apt; then
        sudo apt install -y python3 python3-pip python3-venv python3-pyqt5 python3-pyqt6 sqlite3
    elif command_exists dnf; then
        sudo dnf install -y python3 python3-pip python3-virtualenv python3-qt5 python3-qt6 sqlite
    else
        echo "Neither apt nor dnf package manager found. Exiting."
        exit 1
    fi
}