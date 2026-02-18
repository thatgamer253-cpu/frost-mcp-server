from duckduckgo_search import DDGS

def search_web(query, max_results=5):
    """
    Performs a web search using DuckDuckGo.
    Returns a list of dictionaries [{'title':..., 'href':..., 'body':...}]
    """
    try:
        results = DDGS().text(query, max_results=max_results)
        if not results:
            return []
        # Ensure list of dicts
        out = []
        for r in results:
            out.append({
                "title": r.get("title", ""),
                "href": r.get("href", ""),
                "body": r.get("body", "")
            })
        return out
    except Exception as e:
        print(f"Search Error: {e}")
        return []
