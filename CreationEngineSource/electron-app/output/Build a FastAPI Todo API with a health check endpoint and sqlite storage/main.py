import sys
from name_analysis import analyze_name
from data_visualization import visualize_data
from similarity import calculate_similarity
from error_handling import handle_error
from cache import Cache
from config import load_config

def main():
    try:
        # Load configuration
        config = load_config('config.json')
        
        # Initialize cache
        cache = Cache(config['cache_settings'])

        # CLI interaction
        if len(sys.argv) < 2:
            print("Usage: python main.py <command> [options]")
            sys.exit(1)

        command = sys.argv[1]

        if command == 'analyze':
            if len(sys.argv) < 3:
                print("Usage: python main.py analyze <name>")
                sys.exit(1)
            name = sys.argv[2]
            result = analyze_name(name)
            print(f"Analysis Result: {result}")

        elif command == 'visualize':
            if len(sys.argv) < 3:
                print("Usage: python main.py visualize <data>")
                sys.exit(1)
            data = sys.argv[2]
            visualize_data(data)

        elif command == 'similarity':
            if len(sys.argv) < 4:
                print("Usage: python main.py similarity <string1> <string2>")
                sys.exit(1)
            string1 = sys.argv[2]
            string2 = sys.argv[3]
            similarity_score = calculate_similarity(string1, string2)
            print(f"Similarity Score: {similarity_score}")

        else:
            print(f"Unknown command: {command}")
            sys.exit(1)

    except Exception as e:
        handle_error(e)

if __name__ == "__main__":
    main()