import random

def generate_scenes(genre):
    """
    Generate a list of scene descriptions based on the given genre.

    :param genre: The genre of the script (e.g., "Action", "Comedy", "Drama").
    :return: A list of scene descriptions.
    """
    try:
        # Define possible scenes for different genres
        genre_scenes = {
            "Action": [
                "A high-speed chase through the city.",
                "An intense hand-to-hand combat in a dimly lit warehouse.",
                "A daring rescue mission in a hostile environment."
            ],
            "Comedy": [
                "A hilarious misunderstanding at a dinner party.",
                "A comedic mishap at a wedding ceremony.",
                "A series of unfortunate yet funny events at a family reunion."
            ],
            "Drama": [
                "A tense confrontation between old friends.",
                "An emotional breakdown in a hospital room.",
                "A heartfelt confession in a quiet café."
            ]
        }

        # Select scenes based on the genre
        scenes = genre_scenes.get(genre, ["A generic scene in an unspecified setting."])
        
        # Randomly select a subset of scenes
        selected_scenes = random.sample(scenes, min(3, len(scenes)))
        
        return selected_scenes
    except Exception as e:
        print(f"An error occurred while generating scenes: {e}")
        return []