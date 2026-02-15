from name_analysis_module import analyze_name, get_cultural_origin, check_name_popularity, get_name_meaning

try:
    name = input("Enter a name: ")

    # Analyze name details
    analysis = analyze_name(name)
    print(f"Name Analysis: {analysis}")

    # Get cultural origin
    cultural_origin = get_cultural_origin(name)
    print(f"Cultural Origin: {cultural_origin}")

    # Check name popularity
    popularity = check_name_popularity(name)
    print(f"Name Popularity: {popularity}")

    # Get name meaning
    meaning = get_name_meaning(name)
    print(f"Name Meaning: {meaning}")

except Exception as e:
    print(f"An error occurred: {e}")