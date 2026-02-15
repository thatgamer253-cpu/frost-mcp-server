import sys
from quote_service import QuoteService, Quote

def main() -> None:
    """
    Main entry point for the random quote generator application.
    Retrieves and prints a random inspirational quote.
    """
    try:
        quote_service = QuoteService()
        quote: Quote | None = quote_service.get_random_quote()

        if quote:
            print(f"\"{quote.text}\" - {quote.author}")
        else:
            # This case indicates that the service could not provide a quote,
            # possibly due to an empty data source or an internal issue.
            print("Error: Could not retrieve a quote. The quote list might be empty or unavailable.", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        # Catching a broad Exception for any unexpected issues during service instantiation
        # or quote retrieval. More specific exceptions could be caught if defined
        # and raised by QuoteService (e.g., NoQuotesAvailableError).
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()