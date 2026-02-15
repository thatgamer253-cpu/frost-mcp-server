# README_PRODUCT.md

## Overview

Welcome to the Media Management Application! This application is designed to help you manage, process, and export media files efficiently. It comes with a robust plugin system that allows you to extend its functionality easily.

## Features

- **Media Library Management**: Load, tag, and manage metadata for your media files.
- **Image Processing**: Resize, apply filters, and save images using the Image Engine.
- **Batch Processing**: Automate tasks across multiple media files.
- **Export Manager**: Export media files to specified destinations with ease.
- **Plugin System**: Discover, load, activate, and deactivate plugins to extend application capabilities.
- **User Interface**: Intuitive UI built with PyQt5 for managing settings, plugins, and media library.

## Installation

### Prerequisites

- Python 3.8 or higher
- Virtual environment tool (e.g., `venv` or `virtualenv`)

### Steps

1. **Clone the Repository**

   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. **Set Up Virtual Environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**

   Copy the `.env.example` to `.env` and configure your environment variables as needed.

   ```bash
   cp .env.example .env
   ```

5. **Run the Application**

   ```bash
   python app.py
   ```

## Configuration

The application uses environment variables for configuration. Key variables include:

- `PLUGINS_DIRECTORY`: Directory where plugins are stored.
- `EXPORT_PATH`: Default path for exporting media files.
- `MEDIA_LIBRARY_PATH`: Path to the media library.

These can be set in the `.env` file.

## Usage

### User Interface

- **Main Window**: Access the main features of the application.
- **Settings**: Configure application settings.
- **Plugin Manager**: Manage plugins, including activation and deactivation.
- **Media Library**: View and manage your media files.

### Plugin System

1. **Discover Plugins**: Automatically detects plugins in the specified directory.
2. **Load Plugins**: Dynamically loads plugins using Python's `importlib`.
3. **Activate/Deactivate Plugins**: Use the UI to activate or deactivate plugins.

### Exporting Media

Use the Export Manager to export media files to your desired location. Ensure the destination directory exists or let the application create it for you.

## Error Handling and Logging

The application includes comprehensive error handling and logging. Logs are stored in a structured format to aid in debugging and monitoring.

## Contributing

We welcome contributions! Please fork the repository and submit a pull request with your changes. Ensure all new code includes appropriate error handling and logging.

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Support

For support, please open an issue in the GitHub repository or contact the maintainers directly.