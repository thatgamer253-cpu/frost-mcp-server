# llm/gpt4.py

import openai
from typing import List, Dict

class GPT4:
    def __init__(self, api_key: str):
        self.api_key = api_key
        openai.api_key = api_key

    def generate_response(self, prompt: str) -> str:
        # Check if the prompt exceeds the maximum context length
        max_context_length = 4096  # Example value, adjust as needed
        if len(prompt) > max_context_length:
            prompt = prompt[:max_context_length]
            print(f"Prompt truncated to fit within {max_context_length} characters.")

        try:
            response = openai.Completion.create(
                engine="text-davinci-003",
                prompt=prompt,
                max_tokens=150
            )
            return response.choices[0].text.strip()
        except Exception as e:
            print(f"Error generating response: {e}")
            return None