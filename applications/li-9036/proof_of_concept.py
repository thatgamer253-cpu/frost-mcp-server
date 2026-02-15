```python
# Import necessary libraries
import requests
from bs4 import BeautifulSoup
from transformers import pipeline

# Define a function to scrape a web page and extract text
def scrape_and_summarize(url):
    # Fetch the content from the URL
    response = requests.get(url)
    
    # Parse the content with BeautifulSoup
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Extract text from specific HTML elements, such as paragraphs
    text_content = ' '.join([p.text for p in soup.find_all('p')])

    # Initialize a pre-trained summarization pipeline
    summarizer = pipeline("summarization")
    
    # Summarize the extracted text
    summary = summarizer(text_content, max_length=130, min_length=30, do_sample=False)
    
    # Return the summarized text
    return summary[0]['summary_text']

# Example usage
url = "https://example.com"
summary = scrape_and_summarize(url)
print('Summary:', summary)
```

- The script starts by importing necessary libraries: `requests` for HTTP requests, `BeautifulSoup` for web scraping, and `transformers` for AI model processing.
- It defines a function `scrape_and_summarize()` that accepts a `url` parameter.
- The function fetches the HTML content of the page using `requests.get`.
- It parses this page with BeautifulSoup to extract all text within paragraph (`<p>`) elements.
- Then, it initializes a transformer-based summarization pipeline from Hugging Face's `transformers` library.
- Finally, using this pipeline, it summarizes the extracted text and returns the summary. 
- The example usage section demonstrates how to call the function with a URL and print the summary.