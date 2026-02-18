# llm_integration.py
import openai
import tiktoken

# Define the GPT-4 model and its maximum token limit.
MODEL_NAME = "gpt-4"
MAX_TOKEN_LIMIT = 8192


def truncate_text_to_token_limit(text: str, model_name: str, max_tokens: int) -> str:
    """Truncates the input text to fit within the specified token limit for the given model.

    Args:
        text: The input text to truncate.
        model_name: The name of the OpenAI model.
        max_tokens: The maximum number of tokens allowed for the model.

    Returns:
        The truncated text, or the original text if it's already within the limit.
    """
    encoding = tiktoken.encoding_for_model(model_name)
    encoded_text = encoding.encode(text)
    num_tokens = len(encoded_text)

    if num_tokens > max_tokens:
        truncated_encoded_text = encoded_text[:max_tokens]
        truncated_text = encoding.decode(truncated_encoded_text)
        print(f"Warning: Input text truncated to {max_tokens} tokens.")
        return truncated_text
    else:
        return text


def call_openai_api(prompt: str, model_name: str = MODEL_NAME):
    """Calls the OpenAI API with the given prompt and model.

    Args:
        prompt: The prompt to send to the OpenAI API.
        model_name: The name of the OpenAI model to use.

    Returns:
        The response from the OpenAI API.
    """
    # Truncate the prompt to fit within the token limit.
    truncated_prompt = truncate_text_to_token_limit(prompt, model_name, MAX_TOKEN_LIMIT)

    try:
        response = openai.Completion.create(
            engine=model_name,
            prompt=truncated_prompt,
            max_tokens=150,  # You can adjust this as needed
        )
        return response.choices[0].text.strip()
    except Exception as e:
        print(f"Error: {model_name} (openai) -> {e}")
        return None


if __name__ == '__main__':
    # Example usage
    long_text = "This is a very long text that exceeds the maximum token limit for GPT-4. " * 1000
    response = call_openai_api(long_text)
    if response:
        print("Response:", response)
    else:
        print("No response received.")