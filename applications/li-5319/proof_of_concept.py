```python
# Proof of Concept: AI Engineer (Python, Gen AI)

# Import necessary libraries
import openai
import os

# Set up OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Define a function for a simple text generation task
def generate_text(prompt, model="text-davinci-003", max_tokens=150):
    """
    Generate text using OpenAI's GPT model.
    
    Args:
        prompt (str): The input text prompt to guide the model.
        model (str): The OpenAI model to use for generation.
        max_tokens (int): The maximum number of tokens to generate.

    Returns:
        response (str): The generated text response.
    """
    # Request completion from the OpenAI API
    response = openai.Completion.create(
        engine=model,
        prompt=prompt,
        max_tokens=max_tokens
    )
    
    # Extract and return the generated text
    return response.choices[0].text.strip()

# Example Usage
if __name__ == "__main__":
    # Define a prompt
    prompt = "Explain the importance of machine learning in modern technology."
    
    # Generate text
    generated_text = generate_text(prompt)
    
    # Print the generated response
    print(generated_text)
```

### Comments:
- The script sets up a basic proof of concept for an AI Engineer role focusing on Python and Generative AI.
- **Libraries Used**: `openai` to interface with the OpenAI API for text generation.
- **API Key Setup**: Assumes the OpenAI API key is stored in an environment variable for security.
- **Function `generate_text()`**: Flexible function to generate text from a provided prompt using OpenAI's `text-davinci-003` model.
- **Main Execution**: Demonstrates how to use the function with a sample prompt.