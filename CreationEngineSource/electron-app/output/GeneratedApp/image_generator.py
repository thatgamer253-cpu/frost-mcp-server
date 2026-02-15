import requests
import os
from dotenv import load_dotenv

load_dotenv()

class ImageGenerationError(Exception):
    """Custom exception for image generation errors."""
    pass

def generate_image(prompt):
    """
    Generates an image based on the provided text prompt using a text-to-image API.

    Args:
        prompt (str): The text prompt to generate the image from.

    Returns:
        bytes: The binary content of the generated image.

    Raises:
        ImageGenerationError: If the image generation fails.
    """
    api_url = os.getenv('IMAGE_API_URL')
    api_key = os.getenv('IMAGE_API_KEY')

    if not api_url or not api_key:
        raise ImageGenerationError("API URL or API Key is not set in the environment variables.")

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    payload = {
        'prompt': prompt,
        'num_images': 1
    }

    try:
        response = requests.post(api_url, json=payload, headers=headers)
        response.raise_for_status()
        image_data = response.content
        return image_data
    except requests.exceptions.RequestException as e:
        raise ImageGenerationError(f"Failed to generate image: {e}")