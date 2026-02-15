{"name": name, "api_key": api_key})
        response.raise_for_status()

        data = response.json()
        return data.get("origin", "Unknown")
    except requests.exceptions.RequestException as e:
        return f"Error contacting the cultural origin service: {e}"
    except Exception as e:
        return f"Error determining cultural origin: {e}