# South Park Episode Script Generator

## Project Description

This project is a Python application designed to generate scripts for South Park episodes. Utilizing AI, the application creates dialogue, plot, and character interactions that capture the humor and satire typical of South Park. The generated script is output as a text file, providing a complete episode narrative.

## Features

1. **Character Module**: Defines main characters (e.g., Stan, Kyle, Cartman, Kenny) with unique traits and dialogue styles. Functions like `generate_dialogue(character_name)` produce character-specific lines.
2. **Plot Generator**: The `generate_plot()` function outlines a basic episode structure: introduction, conflict, climax, and resolution, using randomization for unique scenarios.
3. **Dialogue Engine**: `create_scene()` generates scenes with character interactions, ensuring dialogue reflects the show's satirical tone.
4. **Humor and Satire Integration**: A humor module using `textblob` analyzes and injects humor into dialogues.
5. **Script Formatter**: `format_script()` compiles scenes into a cohesive script, outputting to `episode_script.txt`.
6. **CLI Interface**: A command-line interface allows users to specify episode length and main plot themes.
7. **Error Handling**: Implements checks for logical consistency in plot and dialogue, handling edge cases like excessive repetition or inappropriate content.
8. **External API Integration**: Utilizes OpenAI's GPT API for generating creative dialogue and plot elements.

## Installation

1. **Clone the Repository:**