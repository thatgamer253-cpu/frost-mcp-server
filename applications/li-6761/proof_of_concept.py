```python
# Proof of Concept for an AI Engineer (Python, Gen AI) Role

# Import necessary libraries
import openai  # OpenAI API for Generative AI capabilities
import requests  # Requests library for web scraping

# Set up OpenAI API key (replace 'your_api_key' with a valid OpenAI API key)
openai.api_key = 'your_api_key'

# Function to generate text using OpenAI's GPT-3
def generate_text(prompt, max_tokens=100):
    """
    Generate text from a given prompt using OpenAI's text-davinci model.
    """
    # Call to OpenAI API for text generation
    response = openai.Completion.create(
      engine="text-davinci-003",  # Use the latest GPT-3 engine
      prompt=prompt,
      max_tokens=max_tokens
    )
    # Extract and return the generated text
    return response.choices[0].text.strip()

# Function to scrape data from a webpage
def scrape_data(url):
    """
    Scrapes the title from a web page.
    """
    # Send an HTTP GET request to the URL
    response = requests.get(url)
    if response.status_code == 200:
        # Parse the HTML content if the response is successful
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')
        # Extract and return the title of the page
        return soup.title.string
    else:
        return "Failed to retrieve data"

# Example usage
if __name__ == "__main__":
    # Example prompt for text generation
    prompt = "Explain the importance of AI in modern technology"
    generated_text = generate_text(prompt)
    print(f"Generated Text: {generated_text}")

    # URL to scrape
    url = "https://www.example.com"
    scraped_title = scrape_data(url)
    print(f"Scraped Page Title: {scraped_title}")
```
