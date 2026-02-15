# test_app.py
import sys
import os
import pytest

# Add the project root to the sys.path to allow relative imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import initialize_logging, main

def test_initialize_logging_import():
    assert callable(initialize_logging)

def test_main_import():
    assert callable(main)

def test_initialize_logging_execution():
    try:
        initialize_logging()
    except Exception as e:
        pytest.fail(f"initialize_logging() raised an exception: {e}")

def test_main_execution():
    try:
        main()
    except Exception as e:
        pytest.fail(f"main() raised an exception: {e}")

# test_core.py
from core.base_tool import BaseTool
from core.task_manager import TaskManager
from core.plugin_loader import PluginLoader
from core.state_manager import StateManager
from core.error_handler import ErrorHandler

def test_base_tool_import():
    assert BaseTool is not None

def test_task_manager_import():
    assert TaskManager is not None

def test_plugin_loader_import():
    assert PluginLoader is not None

def test_state_manager_import():
    assert StateManager is not None

def test_error_handler_import():
    assert ErrorHandler is not None

# test_tools.py
from tools import initialize_tools

def test_initialize_tools_import():
    assert callable(initialize_tools)

def test_initialize_tools_execution():
    try:
        initialize_tools()
    except Exception as e:
        pytest.fail(f"initialize_tools() raised an exception: {e}")