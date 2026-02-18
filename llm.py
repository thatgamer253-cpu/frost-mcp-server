# llm.py

import openai

# Increase the context length parameter to accommodate longer inputs
def generate_response(prompt):
    max_tokens = 81920  # Increased from default value
    if len(prompt) > max_tokens:
        prompt = prompt[:max_tokens]  # Truncate the input to fit within the allowed limit
    response = openai.Completion.create(
        engine="gpt-4",
        prompt=prompt,
        max_tokens=max_tokens
    )
    return response.choices[0].text.strip()
