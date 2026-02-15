import os

def save_file(title, content):
    try:
        with open(f"{title}.txt", "w") as file:
            file.write(content)
        print(f"'{title}' has been successfully generated and saved.")
    
    except Exception as e:
        print(f"An error occurred: {e}")