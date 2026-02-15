import sys
import os
import pytest

# Insert the path to the project modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import modules to test
from name_analysis import analyze_name, get_name_length, count_vowels_and_consonants, check_phonetic_similarity
from popularity_check import check_name_popularity
from name_meaning import get_name_meaning
from utils import load_configuration, validate_name
from name_analyzer import analyze_name_details, suggest_similar_names
from data_fetcher import DataFetcher
from compatibility import calculate_numerology, analyze_name_compatibility
from config import load_config, validate_name_format

# Test successful imports
def test_imports():
    assert analyze_name
    assert get_name_length
    assert count_vowels_and_consonants
    assert check_phonetic_similarity
    assert check_name_popularity
    assert get_name_meaning
    assert load_configuration
    assert validate_name
    assert analyze_name_details
    assert suggest_similar_names
    assert DataFetcher
    assert calculate_numerology
    assert analyze_name_compatibility
    assert load_config
    assert validate_name_format

# Test function signatures
def test_function_signatures():
    assert callable(analyze_name)
    assert callable(get_name_length)
    assert callable(count_vowels_and_consonants)
    assert callable(check_phonetic_similarity)
    assert callable(check_name_popularity)
    assert callable(get_name_meaning)
    assert callable(load_configuration)
    assert callable(validate_name)
    assert callable(analyze_name_details)
    assert callable(suggest_similar_names)
    assert callable(calculate_numerology)
    assert callable(analyze_name_compatibility)
    assert callable(load_config)
    assert callable(validate_name_format)

# Test basic happy-path execution
def test_analyze_name():
    result = analyze_name("Alice", "Bob")
    assert isinstance(result, dict)

def test_get_name_length():
    length = get_name_length("Alice")
    assert length == 5

def test_count_vowels_and_consonants():
    vowels, consonants = count_vowels_and_consonants("Alice")
    assert vowels == 3
    assert consonants == 2

def test_check_phonetic_similarity():
    similarity = check_phonetic_similarity("Alice", "Alyce")
    assert isinstance(similarity, bool)

def test_check_name_popularity():
    popularity = check_name_popularity("Alice")
    assert isinstance(popularity, dict)

def test_get_name_meaning():
    meaning = get_name_meaning("Alice")
    assert isinstance(meaning, str)

def test_load_configuration():
    config = load_configuration()
    assert isinstance(config, dict)

def test_validate_name():
    is_valid = validate_name("Alice")
    assert isinstance(is_valid, bool)

def test_analyze_name_details():
    details = analyze_name_details("Alice")
    assert isinstance(details, dict)

def test_suggest_similar_names():
    suggestions = suggest_similar_names("Alice")
    assert isinstance(suggestions, list)

def test_data_fetcher():
    fetcher = DataFetcher()
    assert isinstance(fetcher, DataFetcher)

def test_calculate_numerology():
    numerology = calculate_numerology("Alice")
    assert isinstance(numerology, int)

def test_analyze_name_compatibility():
    compatibility = analyze_name_compatibility("Alice", "Bob")
    assert isinstance(compatibility, dict)

def test_load_config():
    config = load_config()
    assert isinstance(config, dict)

def test_validate_name_format():
    is_valid_format = validate_name_format("Alice")
    assert isinstance(is_valid_format, bool)