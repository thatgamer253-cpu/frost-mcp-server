from openai import OpenAI
import os
import sys

# Key from verify_key.py
API_KEY = "AIzaSyA3xrsR1lyTwP88zVRAVVRnKpPqYE1JNqI"
BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

def list_models():
    print(f"Listing models from {BASE_URL}...")
    try:
        client = OpenAI(
            api_key=API_KEY,
            base_url=BASE_URL
        )
        
        models = client.models.list()
        print(f"Found {len(models.data)} models:")
        for m in models.data:
            print(f" - {m.id}")
            
    except Exception as e:
        print(f"ERROR: Failed to list models. {e}")

if __name__ == "__main__":
    list_models()
