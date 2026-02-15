from utils import validate_name
from phonetics import check_phonetic_similarity

numerology_map = {
    'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 8, 'G': 3, 'H': 5, 'I': 1,
    'J': 1, 'K': 2, 'L': 3, 'M': 4, 'N': 5, 'O': 7, 'P': 8, 'Q': 1, 'R': 2,
    'S': 3, 'T': 4, 'U': 6, 'V': 6, 'W': 6, 'X': 5, 'Y': 1, 'Z': 7
}

def calculate_numerology(name):
    name = name.upper()
    numerology_number = sum(numerology_map.get(char, 0) for char in name)
    while numerology_number > 9:
        numerology_number = sum(int(digit) for digit in str(numerology_number))
    return numerology_number

def analyze_name_compatibility(name1, name2):
    """
    Analyzes the compatibility between two names based on numerology and phonetics.

    :param name1: The first name.
    :param name2: The second name.
    :return: A dictionary containing compatibility analysis results.
    """
    try:
        if not (validate_name(name1) and validate_name(name2)):
            raise ValueError("Invalid name format.")

        numerology1 = calculate_numerology(name1)
        numerology2 = calculate_numerology(name2)
        numerology_compatibility = numerology1 == numerology2

        phonetic_similarity = check_phonetic_similarity(name1, name2)

        return {
            "numerology": {
                "name1": numerology1,
                "name2": numerology2,
                "compatible": numerology_compatibility
            },
            "phonetic_similarity": phonetic_similarity
        }

    except Exception as e:
        return {"error": str(e)}