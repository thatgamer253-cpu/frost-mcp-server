import random

class Character:
    def __init__(self, name, trait):
        self.name = name
        self.trait = trait

    def __str__(self):
        return f"{self.name} ({self.trait})"

def generate_characters():
    try:
        names = ["Alice", "Bob", "Charlie", "Diana"]
        traits = ["Brave", "Cunning", "Wise", "Charming"]

        characters = []
        for name in names:
            trait = random.choice(traits)
            characters.append(Character(name, trait))

        return characters

    except Exception as e:
        print(f"An error occurred while generating characters: {e}")
        return []

def generate_character_dialogue(character):
    try:
        dialogues = {
            "Brave": "I will face any challenge head-on!",
            "Cunning": "There's always a way to turn the odds in my favor.",
            "Wise": "Knowledge is the true power.",
            "Charming": "I can win anyone over with a smile."
        }
        return dialogues.get(character.trait, "I have nothing to say.")

    except Exception as e:
        print(f"An error occurred while generating dialogue for {character.name}: {e}")
        return "..."

# Example usage
if __name__ == "__main__":
    characters = generate_characters()
    for character in characters:
        print(character)
        print(generate_character_dialogue(character))