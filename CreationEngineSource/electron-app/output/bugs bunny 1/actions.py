import pygame
from pygame.locals import *
from animation import CharacterAnimation

class CharacterActions:
    def __init__(self, screen, character_sprites_path):
        self.character_animation = CharacterAnimation(screen, character_sprites_path)
        self.position = (100, 100)  # Default position
        self.velocity = (0, 0)  # Default velocity

    def move(self, direction):
        try:
            if direction == 'left':
                self.velocity = (-5, 0)
            elif direction == 'right':
                self.velocity = (5, 0)
            elif direction == 'up':
                self.velocity = (0, -5)
            elif direction == 'down':
                self.velocity = (0, 5)
            else:
                self.velocity = (0, 0)
        except Exception as e:
            print(f"Error setting movement direction: {e}")

    def update_position(self):
        try:
            x, y = self.position
            vx, vy = self.velocity
            self.position = (x + vx, y + vy)
        except Exception as e:
            print(f"Error updating position: {e}")

    def perform_action(self, action):
        try:
            if action == 'jump':
                self.jump()
            elif action == 'attack':
                self.attack()
            else:
                print(f"Unknown action: {action}")
        except Exception as e:
            print(f"Error performing action: {e}")

    def jump(self):
        try:
            print("Character jumps")
            # Implement jump logic here
        except Exception as e:
            print(f"Error during jump: {e}")

    def attack(self):
        try:
            print("Character attacks")
            # Implement attack logic here
        except Exception as e:
            print(f"Error during attack: {e}")

    def animate(self, fps=30):
        try:
            self.update_position()
            self.character_animation.animate(self.position, fps)
        except Exception as e:
            print(f"Error during animation: {e}")

def main():
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption('Character Actions')

    character_actions = CharacterActions(screen, 'path/to/character/sprites')

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            elif event.type == KEYDOWN:
                if event.key == K_LEFT:
                    character_actions.move('left')
                elif event.key == K_RIGHT:
                    character_actions.move('right')
                elif event.key == K_UP:
                    character_actions.move('up')
                elif event.key == K_DOWN:
                    character_actions.move('down')
                elif event.key == K_SPACE:
                    character_actions.perform_action('jump')
                elif event.key == K_a:
                    character_actions.perform_action('attack')

        screen.fill((0, 0, 0))
        character_actions.animate()

    pygame.quit()

if __name__ == "__main__":
    main()