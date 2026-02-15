from collections import defaultdict
from core.base_tool import BaseTool
import logging

class TaskManager:
    def __init__(self, state_manager, plugin_loader):
        self.state_manager = state_manager
        self.plugin_loader = plugin_loader
        self.tasks = defaultdict(list)
        self.logger = logging.getLogger(__name__)

    def add_task(self, task_name, task_instance):
        if not isinstance(task_instance, BaseTool):
            raise ValueError("Task instance must be of type BaseTool")
        self.tasks[task_name].append(task_instance)
        self.logger.info(f"Task {task_name} added.")

    def execute_tasks(self):
        try:
            self.logger.info("Executing tasks in DAG order.")
            for task_name, task_list in self.tasks.items():
                self.logger.info(f"Executing task group: {task_name}")
                for task in task_list:
                    self.logger.info(f"Initializing task: {task}")
                    task.initialize()
                    self.logger.info(f"Executing task: {task}")
                    task.execute()
                    self.logger.info(f"Shutting down task: {task}")
                    task.shutdown()
            self.logger.info("All tasks executed successfully.")
        except Exception as e:
            self.logger.error("Error occurred during task execution.", exc_info=True)
            raise

    def load_tasks_from_plugins(self):
        try:
            self.logger.info("Loading tasks from plugins.")
            plugins = self.plugin_loader.load_plugins()
            for plugin in plugins:
                task_name = plugin.get_task_name()
                task_instance = plugin.get_task_instance()
                self.add_task(task_name, task_instance)
            self.logger.info("Tasks loaded from plugins successfully.")
        except Exception as e:
            self.logger.error("Error occurred while loading tasks from plugins.", exc_info=True)
            raise