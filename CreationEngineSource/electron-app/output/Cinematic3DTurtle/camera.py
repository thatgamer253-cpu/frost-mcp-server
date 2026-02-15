# camera.py

from typing import Tuple
import math

class Camera:
    def __init__(self, position: Tuple[float, float, float] = (0.0, 0.0, 0.0), 
                 rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0)):
        """
        Initialize the camera with a position and rotation.
        
        :param position: A tuple representing the x, y, z coordinates of the camera.
        :param rotation: A tuple representing the pitch, yaw, roll of the camera.
        """
        self.position = position
        self.rotation = rotation

    def move(self, delta: Tuple[float, float, float]):
        """
        Move the camera by a certain delta.
        
        :param delta: A tuple representing the change in x, y, z coordinates.
        """
        try:
            self.position = tuple(map(sum, zip(self.position, delta)))
        except Exception as e:
            print(f"Error moving camera: {e}")

    def rotate(self, delta: Tuple[float, float, float]):
        """
        Rotate the camera by a certain delta.
        
        :param delta: A tuple representing the change in pitch, yaw, roll.
        """
        try:
            self.rotation = tuple(map(sum, zip(self.rotation, delta)))
        except Exception as e:
            print(f"Error rotating camera: {e}")

    def get_view_matrix(self):
        """
        Calculate and return the view matrix based on the current position and rotation.
        
        :return: A 4x4 view matrix as a list of lists.
        """
        try:
            # Placeholder for actual view matrix calculation
            # This would typically involve complex math with rotation matrices
            view_matrix = [[1, 0, 0, -self.position[0]],
                           [0, 1, 0, -self.position[1]],
                           [0, 0, 1, -self.position[2]],
                           [0, 0, 0, 1]]
            return view_matrix
        except Exception as e:
            print(f"Error calculating view matrix: {e}")
            return None