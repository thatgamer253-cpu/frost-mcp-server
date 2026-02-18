from openai import OpenAI
import sys

API_KEY = "AIzaSyA3xrsR1lyTwP88zVRAVVRnKpPqYE1JNqI"
BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

def verify():
    print(f"Testing key: {API_KEY[:10]}...")
    try:
        client = OpenAI(
            api_key=API_KEY,
            base_url=BASE_URL
        )
        
        response = client.chat.completions.create(
            model="gemini-2.0-flash",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Reply with 'VERIFIED'."}
            ]
        )
        
        content = response.choices[0].message.content
        print(f"Response: {content}")
        if "VERIFIED" in content:
            print("SUCCESS: Key is valid and working.")
            return True
        else:
            print("WARNING: Unexpected response content.")
            return False
            
    except Exception as e:
        print(f"ERROR: Key verification failed. {e}")
        return False

if __name__ == "__main__":
    success = verify()
    sys.exit(0 if success else 1)
