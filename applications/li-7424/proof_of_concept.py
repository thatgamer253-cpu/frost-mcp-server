```python
# Proof of Concept: AI Engineer (Python, Gen AI)

# Required Libraries
import openai  # For generative AI capabilities
import os  # For environment variable management
from bs4 import BeautifulSoup  # For web scraping functionality
import requests  # For making HTTP requests

# Step 1: Set up OpenAI API key
# Usually stored as an environment variable for security purposes
openai.api_key = os.getenv('OPENAI_API_KEY')

# Step 2: Function for Generative AI Task
def generate_response(prompt):
    """
    Uses OpenAI's GPT to generate a response based on the input prompt.
    """
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=prompt,
        max_tokens=150
    )
    return response.choices[0].text.strip()

# Step 3: Scraping Function
def scrape_website(url):
    """
    Scrapes the specified URL and returns the parsed HTML content.
    """
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    return soup

# Example of how to use these functions

# Generative AI Example
prompt_example = "What are the latest trends in AI technology?"
ai_response = generate_response(prompt_example)
print("AI Response:\n", ai_response)

# Web Scraping Example
url_example = "https://example.com"
scraped_content = scrape_website(url_example)
print("Scraped Content:\n", scraped_content.prettify()[:500])  # Print first 500 characters

# Notes:
# 1. Install required packages: `pip install openai beautifulsoup4 requests`
# 2. Ensure to have an OpenAI API key stored in environment variables.
```