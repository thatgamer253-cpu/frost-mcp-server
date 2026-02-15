```python
# PoC for AI Engineer Role - Gen AI with Python Task

import requests
from bs4 import BeautifulSoup
from transformers import GPT2LMHeadModel, GPT2Tokenizer

# Step 1: Web scraping with BeautifulSoup to gather data for training or inference
def scrape_website(url):
    # Send a request to the website
    response = requests.get(url)
    
    # Check if the request to the website was successful
    if response.status_code == 200:
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all the paragraphs on the page
        paragraphs = soup.find_all('p')
        
        # Extract and return text from the paragraphs
        text_content = [para.get_text() for para in paragraphs]
        return " ".join(text_content)
    else:
        raise Exception('Failed to retrieve contents')

# Step 2: Implementing a simple generative AI function using GPT-2
def generate_text(prompt, max_length=50):
    # Load the pre-trained GPT-2 model and tokenizer
    tokenizer = GPT2Tokenizer.from_pretrained('gpt2')
    model = GPT2LMHeadModel.from_pretrained('gpt2')
    
    # Encode the input prompt
    input_ids = tokenizer.encode(prompt, return_tensors='pt')
    
    # Generate text
    output = model.generate(input_ids, max_length=max_length, num_return_sequences=1)
    
    # Decode the generated text
    generated_text = tokenizer.decode(output[0], skip_special_tokens=True)
    return generated_text

# Example usage:
# url = "https://example.com"
# scraped_data = scrape_website(url)
# print(scraped_data)

# prompt = "Once upon a time"
# generated = generate_text(prompt)
# print(generated)
```

This script provides a basic foundation for web scraping using BeautifulSoup and a text generation function using a pre-trained GPT-2 model from the Transformers library. The script follows these steps:

1. Web Scraping: Utilize Python's `requests` library to fetch HTML data from a given URL and parse it with `BeautifulSoup` to extract textual content.

2. Generative AI: Set up a simple text generation using GPT-2 from the Hugging Face Transformers. It tokenizes the input prompt, generates text up to a specified maximum length, and then decodes the tokens back to human-readable text.