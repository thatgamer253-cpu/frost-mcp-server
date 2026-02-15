import time

def count_to_ten():
    try:
        for number in range(1, 11):
            print(number)
            time.sleep(1)
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    count_to_ten()