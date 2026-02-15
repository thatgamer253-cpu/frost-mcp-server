import math
from typing import List, Tuple

class TurtleEngine:
    def __init__(self):
        self.position = (0, 0)
        self.angle = 0  # Angle in degrees
        self.pen_down = True
        self.path = []

    def parse_command(self, command: str):
        try:
            parts = command.strip().lower().split()
            if not parts:
                return

            cmd = parts[0]
            if cmd == "move":
                distance = float(parts[1])
                self.move(distance)
            elif cmd == "turn":
                angle = float(parts[1])
                self.turn(angle)
            elif cmd == "pen":
                state = parts[1]
                self.set_pen(state)
            else:
                print(f"Unknown command: {cmd}")
        except (IndexError, ValueError) as e:
            print(f"Error parsing command '{command}': {e}")

    def move(self, distance: float):
        try:
            radian_angle = math.radians(self.angle)
            dx = distance * math.cos(radian_angle)
            dy = distance * math.sin(radian_angle)
            new_position = (self.position[0] + dx, self.position[1] + dy)
            if self.pen_down:
                self.path.append((self.position, new_position))
            self.position = new_position
        except Exception as e:
            print(f"Error moving turtle: {e}")

    def turn(self, angle: float):
        try:
            self.angle = (self.angle + angle) % 360
        except Exception as e:
            print(f"Error turning turtle: {e}")

    def set_pen(self, state: str):
        try:
            if state == "down":
                self.pen_down = True
            elif state == "up":
                self.pen_down = False
            else:
                print(f"Unknown pen state: {state}")
        except Exception as e:
            print(f"Error setting pen state: {e}")

    def generate_pattern(self, commands: List[str]):
        try:
            for command in commands:
                self.parse_command(command)
        except Exception as e:
            print(f"Error generating pattern: {e}")

    def get_path(self) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
        return self.path