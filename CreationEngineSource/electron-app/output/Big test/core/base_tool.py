class BaseTool:
    """
    BaseTool is an abstract class that all plugins must inherit from.
    It defines the basic interface and lifecycle for plugins.
    """

    def __init__(self, name, version):
        """
        Initialize the BaseTool with a name and version.

        :param name: The name of the tool.
        :param version: The version of the tool.
        """
        self.name = name
        self.version = version

    def initialize(self):
        """
        Initialize the tool. This method should be overridden by subclasses.
        """
        raise NotImplementedError("The initialize method must be overridden by the subclass.")

    def execute(self, *args, **kwargs):
        """
        Execute the tool's main functionality. This method should be overridden by subclasses.

        :param args: Positional arguments for execution.
        :param kwargs: Keyword arguments for execution.
        """
        raise NotImplementedError("The execute method must be overridden by the subclass.")

    def shutdown(self):
        """
        Shutdown the tool and perform any necessary cleanup. This method should be overridden by subclasses.
        """
        raise NotImplementedError("The shutdown method must be overridden by the subclass.")