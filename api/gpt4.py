# api/gpt4.py

import openai

def generate_response(prompt):
    try:
        # Split the prompt into chunks if it exceeds the maximum context length
        max_context_length = 8192  # Increased GPT-4's maximum context length to accommodate longer inputs
        if len(prompt) > max_context_length:
            responses = []
            for i in range(0, len(prompt), max_context_length):
                chunk = prompt[i:i + max_context_length]
                response = openai.Completion.create(
                    engine="gpt-4",
                    prompt=chunk,
                    max_tokens=2048  # Increased from default to accommodate longer inputs
                )
                responses.append(response.choices[0].text.strip())
            return ' '.join(responses)
        else:
            response = openai.Completion.create(
                engine="gpt-4",
                prompt=prompt,
                max_tokens=2048  # Increased from default to accommodate longer inputs
            )
            return response.choices[0].text.strip()
    except Exception as e:
        print(f"Error: {e}")
        return None