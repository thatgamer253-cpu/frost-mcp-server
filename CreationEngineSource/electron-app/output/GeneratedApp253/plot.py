import random

def generate_plot():
    try:
        # Define possible settings, conflicts, and resolutions
        settings = [
            "a bustling city", 
            "a quiet village", 
            "a mysterious forest", 
            "a distant planet"
        ]
        conflicts = [
            "a looming threat", 
            "a personal vendetta", 
            "a race against time", 
            "a forbidden love"
        ]
        resolutions = [
            "a surprising alliance", 
            "a sacrifice for the greater good", 
            "an unexpected discovery", 
            "a return to normalcy"
        ]

        # Randomly select elements to form the plot
        setting = random.choice(settings)
        conflict = random.choice(conflicts)
        resolution = random.choice(resolutions)

        # Construct the plot structure
        plot = {
            "setting": setting,
            "conflict": conflict,
            "resolution": resolution
        }

        return plot

    except Exception as e:
        print(f"An error occurred while generating the plot: {e}")
        return {
            "setting": "unknown",
            "conflict": "unknown",
            "resolution": "unknown"
        }