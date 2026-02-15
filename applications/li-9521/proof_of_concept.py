```python
# Proof of Concept for an AI Engineer (Python, Gen AI) - Functional Python Script Template

# Import necessary libraries
import requests
from bs4 import BeautifulSoup
from transformers import pipeline

# Define the URL for scraping
url = 'https://example.com/articles'

# Function to perform web scraping
def scrape_articles(url):
    # Send a GET request to the URL
    response = requests.get(url)
    
    # Check if the request was successful
    if response.status_code == 200:
        # Parse the content with BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract article titles for example (Modify based on actual HTML structure)
        articles = soup.find_all('h2', class_='article-title')
        article_titles = [article.get_text() for article in articles]
        
        return article_titles
    else:
        # Return an empty list if the request failed
        return []

# Function to generate a summary from the scraped data using Gen AI
def generate_summary(text):
    # Initialize a text summarization pipeline
    summarizer = pipeline('summarization')
    
    # Generate a summary of the input text
    summary = summarizer(text, max_length=50, min_length=25, do_sample=False)
    
    return summary[0]['summary_text']

# Main execution
if __name__ == '__main__':
    # Scrape article titles from the given URL
    article_titles = scrape_articles(url)
    
    # Print each article title and its AI-generated summary
    for title in article_titles:
        print(f"Title: {title}")
        print("Summary:", generate_summary(title))
        print('-' * 50)
```
