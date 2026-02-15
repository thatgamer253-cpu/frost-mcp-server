import pygame
from pygame.locals import *
import os

class CharacterAnimation:
    def __init__(self, screen, character_sprites_path):
        self.screen = screen
        self.character_sprites_path = character_sprites_path
        self.sprites = []
        self.current_sprite_index = 0
        self.load_sprites()
        self.clock = pygame.time.Clock()

    def load_sprites(self):
        try:
            for file_name in sorted(os.listdir(self.character_sprites_path)):
                if file_name.endswith('.png'):
                    image = pygame.image.load(os.path.join(self.character_sprites_path, file_name))
                    self.sprites.append(image)
        except Exception as e:
            print(f"Error loading sprites: {e}")

    def update(self):
        try:
            self.current_sprite_index += 1
            if self.current_sprite_index >= len(self.sprites):
                self.current_sprite_index = 0
        except Exception as e:
            print(f"Error updating sprite index: {e}")

    def render(self, position):
        try:
            sprite = self.sprites[self.current_sprite_index]
            self.screen.blit(sprite, position)
        except Exception as e:
            print(f"Error rendering sprite: {e}")

    def animate(self, position, fps=30):
        try:
            self.update()
            self.render(position)
            pygame.display.flip()
            self.clock.tick(fps)
        except Exception as e:
            print(f"Error during animation: {e}")

def main():
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption('Character Animation')

    character_animation = CharacterAnimation(screen, 'path/to/character/sprites')

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False

        screen.fill((0, 0, 0))
        character_animation.animate((100, 100))

    pygame.quit()

if __name__ == "__main__":
    main()