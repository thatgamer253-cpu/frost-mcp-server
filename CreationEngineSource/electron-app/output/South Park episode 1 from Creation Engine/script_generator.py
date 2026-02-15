import os
import openai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Retrieve the OpenAI API key from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def generate_script(topic):
    """
    Generates a script based on the provided topic using the GPT-3.5 API.

    Args:
        topic (str): The topic for which to generate the script.

    Returns:
        str: The generated script text.
    """
    if not OPENAI_API_KEY:
        raise ValueError("OpenAI API key is not set. Please check your .env file.")

    try:
        openai.api_key = OPENAI_API_KEY

        # Call the OpenAI API to generate a script
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=f"Write a detailed script about {topic}.",
            max_tokens=500,
            n=1,
            stop=None,
            temperature=0.7
        )

        # Extract the script text from the response
        script_text = response.choices[0].text.strip()
        return script_text

    except openai.error.OpenAIError as e:
        print(f"OpenAI API error: {e}")
        raise

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise