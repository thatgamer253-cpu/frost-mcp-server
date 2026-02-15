from .agent import Agent
from .camera import Camera
from .collision import CollisionDetector
from .graphics import GraphicsEngine
from .ui import MainUI
from .log import setup_logging
from .physics import PhysicsEngine
from .parameters import Parameters
from .widgets import CustomWidget

__all__ = [
    "Agent",
    "Camera",
    "CollisionDetector",
    "GraphicsEngine",
    "MainUI",
    "setup_logging",
    "PhysicsEngine",
    "Parameters",
    "CustomWidget"
]

# Initialize logging
setup_logging()

# Initialize parameters
parameters = Parameters()

# Initialize the main components
camera = Camera()
graphics_engine = GraphicsEngine()
physics_engine = PhysicsEngine()
collision_detector = CollisionDetector()

# Initialize the UI
main_ui = MainUI()

# Initialize custom widgets
custom_widget = CustomWidget()

# Initialize the agent
agent = Agent(camera=camera, graphics_engine=graphics_engine, physics_engine=physics_engine, collision_detector=collision_detector)

# The package is now ready to be used in the main application
# Ensure all components are properly initialized and ready for interaction