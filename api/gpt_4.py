# api/gpt_4.py

import openai

def generate_response(prompt):
    # Set the maximum context length parameter to accommodate longer inputs
    max_context_length = 8192  # Increased from default value

    try:
        response = openai.Completion.create(
            engine="gpt-4",
            prompt=prompt,
            max_tokens=max_context_length
        )
        return response.choices[0].text.strip()
    except Exception as e:
        print(f"Error: {e}")
        return None