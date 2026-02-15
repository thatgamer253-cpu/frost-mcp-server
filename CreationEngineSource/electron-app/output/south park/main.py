import sys

def main():
    try:
        # Your main code logic here
        print("Hello, World!")
    except Exception as e:
        print(f"An error occurred: {str(e)}", file=sys.stderr)

if __name__ == "__main__":
    main()