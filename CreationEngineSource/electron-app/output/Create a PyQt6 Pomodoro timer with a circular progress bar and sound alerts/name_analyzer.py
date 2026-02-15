from name_analysis import analyze_name, check_phonetic_similarity, count_vowels_and_consonants, get_name_length
from popularity_check import check_name_popularity
from utils import validate_name
from name_meaning import get_name_meaning

def analyze_name_details(name):
    """
    Analyzes the details of a given name including its length, vowel and consonant count,
    and phonetic similarity to other names.

    :param name: The name to analyze.
    :return: A dictionary containing the analysis results.
    """
    try:
        if not validate_name(name):
            raise ValueError("Invalid name format.")

        analysis = analyze_name(name)
        length = get_name_length(name)
        vowels, consonants = count_vowels_and_consonants(name)
        popularity = check_name_popularity(name)

        return {
            "analysis": analysis,
            "length": length,
            "vowels": vowels,
            "consonants": consonants,
            "popularity": popularity
        }
    except Exception as e:
        return {"error": str(e)}

def suggest_similar_names(name):
    """
    Suggests similar names based on phonetic similarity.

    :param name: The name to find similar names for.
    :return: A list of similar names.
    """
    try:
        if not validate_name(name):
            raise ValueError("Invalid name format.")

        # Mocked similar names for demonstration purposes
        similar_names = ["Alice", "Alicia", "Alison", "Alyssa"]
        similar_names = [n for n in similar_names if check_phonetic_similarity(name, n)]

        return similar_names
    except Exception as e:
        return {"error": str(e)}