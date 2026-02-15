# name_analysis.py

import re
from collections import Counter
from difflib import SequenceMatcher

def analyze_name(name, reference_name="John"):
    """
    Analyzes the given name for various characteristics.

    :param name: The name to analyze.
    :param reference_name: The reference name for phonetic comparison.
    :return: A dictionary containing the analysis results.
    """
    try:
        length = get_name_length(name)
        vowel_count, consonant_count = count_vowels_and_consonants(name)
        phonetic_similarity = check_phonetic_similarity(name, reference_name)

        return {
            "length": length,
            "vowel_count": vowel_count,
            "consonant_count": consonant_count,
            "phonetic_similarity": phonetic_similarity
        }
    except Exception as e:
        raise ValueError(f"Error analyzing name: {e}")

def get_name_length(name):
    """
    Returns the length of the name.

    :param name: The name to measure.
    :return: The length of the name.
    """
    return len(name)

def count_vowels_and_consonants(name):
    """
    Counts the vowels and consonants in the name.

    :param name: The name to analyze.
    :return: A tuple containing the count of vowels and consonants.
    """
    vowels = "aeiouAEIOU"
    vowel_count = sum(1 for char in name if char in vowels)
    consonant_count = sum(1 for char in name if char.isalpha() and char not in vowels)
    return vowel_count, consonant_count

def check_phonetic_similarity(name, reference_name):
    """
    Checks the phonetic similarity of the name with a reference name.

    :param name: The name to compare.
    :param reference_name: The reference name for phonetic comparison.
    :return: A similarity score between 0 and 1.
    """
    return SequenceMatcher(None, name.lower(), reference_name.lower()).ratio()