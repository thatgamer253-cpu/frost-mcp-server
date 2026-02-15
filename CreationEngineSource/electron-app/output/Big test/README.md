# Aura-Nexus

Aura-Nexus is a modular, asynchronous Python-based Autonomous Task Orchestrator. It is designed to receive high-level goals, decompose them into sub-tasks, and execute them using dynamic tool-calling. The architecture is based on a Directed Acyclic Graph (DAG) for task execution, ensuring efficient and non-cyclic task management.

## Features

- **Task Decomposition**: Breaks down high-level goals into manageable sub-tasks using a DAG structure.
- **State Management**: Tracks task statuses (Pending, Running, Completed, Failed) using a local SQLite database.
- **Asynchronous Execution**: Utilizes `asyncio` and `aiohttp` for non-blocking API interactions.
- **Plugin System**: Allows new tools to be added to a `/tools` folder and auto-registered via a directory-based plugin loader.
- **Self-Healing Mechanism**: Provides fixes or workarounds if a tool fails.
- **Security**: Masks all environment variables and uses a `config.yaml` for non-sensitive settings.
- **Caching**: Avoids redundant API calls by using cached results from the SQLite DB if available within the last 60 minutes.
- **Documentation**: Includes a comprehensive README.md with a "How it Works" diagram using Mermaid.js.

## Technical Architecture

- **Core Logic**: BaseTool class in `core/base_tool.py` that all plugins must inherit from.
- **Task Management**: Task management logic in `core/task_manager.py`, utilizing a DAG structure.
- **Plugin Loader**: Dynamically loads tools from the `/tools` directory using `core/plugin_loader.py`.
- **State Management**: Handles task statuses with SQLite in `core/state_manager.py`.
- **Error Handling**: Implements error handling and self-healing logic in `core/error_handler.py`.
- **Main Entry Point**: `app.py` serves as the main entry point, initializing the system and starting task execution.

## UI/UX Details

- **Command-Line Interface**: Provides a CLI for users to input high-level goals and view task statuses.
- **Logging**: Offers real-time feedback on task execution and errors.

## Error Handling and Edge Cases

- Retries failed tasks with exponential backoff.
- Handles network failures gracefully with appropriate error messages.
- Ensures data integrity in the SQLite database during concurrent access.

## Data Flow

1. User inputs a high-level goal via the CLI.
2. The system decomposes the goal into sub-tasks using the DAG structure.
3. Tasks are executed asynchronously, with statuses tracked in the SQLite database.
4. Results are cached and reused when applicable.

## External Libraries/APIs

- `asyncio` and `aiohttp` for asynchronous operations.
- SQLite for local database management.
- PyYAML for configuration file parsing.

## Installation

1. Clone the repository: