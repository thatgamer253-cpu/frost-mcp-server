import pygame
import os

class Scene:
    def __init__(self, screen, background_image_path=None):
        self.screen = screen
        self.background = None
        self.props = []
        if background_image_path:
            self.load_background(background_image_path)

    def load_background(self, image_path):
        try:
            if os.path.exists(image_path):
                self.background = pygame.image.load(image_path).convert()
            else:
                raise FileNotFoundError(f"Background image not found: {image_path}")
        except Exception as e:
            print(f"Error loading background: {e}")

    def add_prop(self, prop):
        if isinstance(prop, pygame.sprite.Sprite):
            self.props.append(prop)
        else:
            print("Invalid prop: Must be a pygame.sprite.Sprite instance")

    def render(self):
        try:
            if self.background:
                self.screen.blit(self.background, (0, 0))
            for prop in self.props:
                prop.update()
                self.screen.blit(prop.image, prop.rect)
        except Exception as e:
            print(f"Error rendering scene: {e}")

    def clear_props(self):
        self.props.clear()