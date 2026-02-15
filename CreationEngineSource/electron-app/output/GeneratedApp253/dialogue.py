import random
from characters import generate_character_dialogue

def generate_dialogue(characters):
    try:
        humor_lines = [
            "Why don't scientists trust atoms? Because they make up everything!",
            "I told my computer I needed a break, and now it won't stop sending me KitKat ads.",
            "Parallel lines have so much in common. It’s a shame they’ll never meet.",
            "I would tell you a construction joke, but I'm still working on it."
        ]

        dialogue_script = []
        for character in characters:
            character_dialogue = generate_character_dialogue(character)
            humor = random.choice(humor_lines)
            dialogue_script.append(f"{character}: {character_dialogue} Also, here's a joke: {humor}")

        return dialogue_script

    except Exception as e:
        print(f"An error occurred while generating dialogue: {e}")
        return ["Dialogue generation failed."]