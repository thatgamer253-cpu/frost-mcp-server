```python
# This is a functional Python script as a Proof of Concept for an AI Engineer role,
# focusing on Generative AI and web scraping using Python.

# Required Libraries
import requests
from bs4 import BeautifulSoup
from transformers import pipeline, GPT2LMHeadModel, GPT2Tokenizer

# Function to scrape text data from a web page
def scrape_website(url):
    # Send HTTP request to the given URL
    response = requests.get(url)
    # Parse HTML content
    soup = BeautifulSoup(response.content, 'html.parser')
    # Extract all paragraphs
    paragraphs = soup.find_all('p')
    # Concatenate the text content of paragraphs
    text_data = ' '.join([para.get_text() for para in paragraphs])
    return text_data

# Function to generate text using a pre-trained Generative AI model
def generate_text(prompt, max_length=100):
    # Load a pre-trained GPT-2 model and tokenizer from Hugging Face model hub
    model_name = "gpt2"
    model = GPT2LMHeadModel.from_pretrained(model_name)
    tokenizer = GPT2Tokenizer.from_pretrained(model_name)
    
    # Encode the prompt text and generate text
    input_ids = tokenizer.encode(prompt, return_tensors='pt')
    # Generate text using model
    output = model.generate(input_ids, max_length=max_length, num_return_sequences=1, no_repeat_ngram_size=2)
    # Decode and return the generated text
    return tokenizer.decode(output[0], skip_special_tokens=True)

# Example Usage
if __name__ == "__main__":
    # URL to scrape
    url = 'https://example.com'
    # Scrape the website
    extracted_text = scrape_website(url)
    print("Extracted Text: ", extracted_text)
    
    # Generative AI prompt
    prompt = "The future of AI in technology is"
    # Generate text based on prompt
    generated_text = generate_text(prompt)
    print("Generated Text: ", generated_text)
```

- This script includes a web scraping function using BeautifulSoup to extract text from web pages.
- It integrates a pre-trained Generative AI model for text generation using Hugging Face's Transformers library.
- The example demonstrates usage by scraping a sample website and generating text from a given prompt.