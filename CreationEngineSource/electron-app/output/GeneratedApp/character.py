# character.py

from PIL import Image, ImageDraw
import random

class Character:
    def __init__(self, name, hair_style, clothing_style, accessories=None):
        self.name = name
        self.hair_style = hair_style
        self.clothing_style = clothing_style
        self.accessories = accessories if accessories else []

    def customize_hair(self, new_hair_style):
        self.hair_style = new_hair_style

    def customize_clothing(self, new_clothing_style):
        self.clothing_style = new_clothing_style

    def add_accessory(self, accessory):
        if accessory not in self.accessories:
            self.accessories.append(accessory)

    def remove_accessory(self, accessory):
        if accessory in self.accessories:
            self.accessories.remove(accessory)

    def generate_character_image(self):
        try:
            # Create a blank image with white background
            image = Image.new('RGB', (200, 400), 'white')
            draw = ImageDraw.Draw(image)

            # Draw a simple representation of the character
            # Head
            draw.ellipse((75, 50, 125, 100), fill='peachpuff', outline='black')
            # Body
            draw.rectangle((75, 100, 125, 300), fill=self.clothing_style, outline='black')
            # Hair
            draw.rectangle((75, 30, 125, 60), fill=self.hair_style, outline='black')

            # Add accessories
            for accessory in self.accessories:
                x = random.randint(50, 150)
                y = random.randint(100, 300)
                draw.text((x, y), accessory, fill='black')

            return image
        except Exception as e:
            print(f"Error generating character image: {e}")
            return None