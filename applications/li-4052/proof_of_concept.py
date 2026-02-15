```python
# Proof of Concept for an AI Engineer Role focused on Gen AI using Python

# Import necessary libraries
import openai  # A popular library to interact with OpenAI's GPT models
import requests
from bs4 import BeautifulSoup  # For web scraping
import os

# Set your OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

def generate_text(prompt):
    """
    Function to generate text using OpenAI's GPT model
    """
    response = openai.Completion.create(
        engine="davinci-codex",  # Choose an appropriate model
        prompt=prompt,  # Input prompt
        max_tokens=100,  # Response length
        n=1,  # Number of responses to generate
        stop=None,  # Stop sequence
        temperature=0.7  # Temperature value to control randomness
    )
    return response.choices[0].text.strip()

def scrape_web_page(url):
    """
    Function to scrape text from a web page using BeautifulSoup
    """
    # Send a GET request to the URL
    response = requests.get(url)
    
    # Parse the content with BeautifulSoup
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Extract text content, here extracting all paragraphs for simplicity
    paragraphs = soup.find_all('p')
    text_content = ' '.join(p.get_text() for p in paragraphs)
    return text_content

# Example usage of both functions
if __name__ == "__main__":
    # Generate text with AI
    ai_text = generate_text(prompt="Write an introduction about Artificial Intelligence")
    print("AI Generated Text:")
    print(ai_text)
    
    # Scrape a web page
    url = "https://example.com"  # Replace with a real URL
    scraped_text = scrape_web_page(url)
    print("Scraped Text from Web Page:")
    print(scraped_text)
```

- The code includes two main functions: `generate_text` using OpenAI's API to create a text based on a given prompt, and `scrape_web_page` which scrapes text content from a webpage using BeautifulSoup. 
- It demonstrates integration with AI and basic web scraping as essential skills for the role.
- An API key is securely retrieved from the environment variables for authentication.