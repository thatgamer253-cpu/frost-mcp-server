# llm_interface.py
import openai
import os
import time
import tiktoken

class LLMInterface:
    def __init__(self, model_name="gpt-4", max_tokens=8192):
        self.model_name = model_name
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set.")
        openai.api_key = self.api_key
        self.max_tokens = max_tokens # Maximum context length for the model
        try:
            self.encoding = tiktoken.encoding_for_model(model_name)
        except:
            self.encoding = tiktoken.get_encoding("cl100k_base")

    def generate_response(self, prompt, max_attempts=3):
        """Generates a response from the LLM.

        Args:
            prompt (str): The prompt to send to the LLM.
            max_attempts (int): The maximum number of attempts to generate a response.

        Returns:
            str: The response from the LLM, or None if all attempts fail.
        """
        for attempt in range(max_attempts):
            try:
                # Truncate the prompt if it exceeds the maximum context length
                truncated_prompt = self.truncate_prompt(prompt)

                response = openai.ChatCompletion.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": truncated_prompt}],
                    temperature=0.7,
                    max_tokens=1000,
                )
                return response.choices[0].message['content']
            except openai.error.OpenAIError as e:
                print(f"Error code: {e.code} - {e.json_body}")
                if attempt < max_attempts - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    print(f"Failed to generate response after {max_attempts} attempts.")
                    return None

    def truncate_prompt(self, prompt):
        """Truncates the prompt to fit within the model's maximum context length.

        Args:
            prompt (str): The prompt to truncate.

        Returns:
            str: The truncated prompt.
        """
        # Use tiktoken to count tokens accurately
        num_tokens = len(self.encoding.encode(prompt))

        if num_tokens > self.max_tokens:
            print("Prompt exceeds maximum token length. Truncating...")
            # Truncate the prompt to fit within the maximum token length
            truncated_prompt = self.encoding.decode(self.encoding.encode(prompt)[:self.max_tokens])
            return truncated_prompt

        return prompt
