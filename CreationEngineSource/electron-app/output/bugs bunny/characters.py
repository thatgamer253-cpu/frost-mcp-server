import random

class Character:
    def __init__(self, name, role, traits):
        self.name = name
        self.role = role
        self.traits = traits

    def __repr__(self):
        return f"Character(name={self.name}, role={self.role}, traits={self.traits})"

def generate_characters(num_characters):
    try:
        roles = ["Protagonist", "Antagonist", "Sidekick", "Mentor", "Love Interest"]
        traits = ["Brave", "Cunning", "Wise", "Charming", "Mysterious"]
        
        characters = []
        for i in range(num_characters):
            name = f"Character_{i+1}"
            role = random.choice(roles)
            character_traits = random.sample(traits, k=2)
            character = Character(name, role, character_traits)
            characters.append(character)
        
        return characters
    except Exception as e:
        print(f"An error occurred while generating characters: {e}")
        return []