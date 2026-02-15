import math
from typing import Tuple, List

class PhysicsEngine:
    def __init__(self, gravity: float = 9.81, friction: float = 0.1):
        """
        Initialize the physics engine with default gravity and friction values.
        
        :param gravity: The gravitational acceleration (m/s^2).
        :param friction: The friction coefficient.
        """
        self.gravity = gravity
        self.friction = friction

    def apply_gravity(self, position: Tuple[float, float, float], velocity: Tuple[float, float, float], delta_time: float) -> Tuple[float, float, float]:
        """
        Apply gravity to the velocity of an object.
        
        :param position: The current position of the object (x, y, z).
        :param velocity: The current velocity of the object (vx, vy, vz).
        :param delta_time: The time step for the simulation.
        :return: The new velocity after applying gravity.
        """
        try:
            vx, vy, vz = velocity
            vy -= self.gravity * delta_time
            return vx, vy, vz
        except Exception as e:
            print(f"Error applying gravity: {e}")
            return velocity

    def apply_friction(self, velocity: Tuple[float, float, float], delta_time: float) -> Tuple[float, float, float]:
        """
        Apply friction to the velocity of an object.
        
        :param velocity: The current velocity of the object (vx, vy, vz).
        :param delta_time: The time step for the simulation.
        :return: The new velocity after applying friction.
        """
        try:
            vx, vy, vz = velocity
            friction_force = self.friction * delta_time
            vx *= (1 - friction_force)
            vz *= (1 - friction_force)
            return vx, vy, vz
        except Exception as e:
            print(f"Error applying friction: {e}")
            return velocity

    def update_position(self, position: Tuple[float, float, float], velocity: Tuple[float, float, float], delta_time: float) -> Tuple[float, float, float]:
        """
        Update the position of an object based on its velocity.
        
        :param position: The current position of the object (x, y, z).
        :param velocity: The current velocity of the object (vx, vy, vz).
        :param delta_time: The time step for the simulation.
        :return: The new position after updating.
        """
        try:
            x, y, z = position
            vx, vy, vz = velocity
            x += vx * delta_time
            y += vy * delta_time
            z += vz * delta_time
            return x, y, z
        except Exception as e:
            print(f"Error updating position: {e}")
            return position

    def simulate(self, position: Tuple[float, float, float], velocity: Tuple[float, float, float], delta_time: float) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
        """
        Simulate the physics for a single time step.
        
        :param position: The current position of the object (x, y, z).
        :param velocity: The current velocity of the object (vx, vy, vz).
        :param delta_time: The time step for the simulation.
        :return: The new position and velocity after the simulation step.
        """
        try:
            velocity = self.apply_gravity(position, velocity, delta_time)
            velocity = self.apply_friction(velocity, delta_time)
            position = self.update_position(position, velocity, delta_time)
            return position, velocity
        except Exception as e:
            print(f"Error during simulation: {e}")
            return position, velocity