import os
import shutil
import time

def setup_test_files():
    print("--- Setting up test files in ./seed_input ---")
    os.makedirs("./seed_input", exist_ok=True)
    
    # 1. Valid Python
    with open("./seed_input/valid_script.py", "w") as f:
        f.write("def hello():\n    print('Hello S&S world')\n\nhello()")
    
    # 2. Syntax Error Python
    with open("./seed_input/broken_syntax.py", "w") as f:
        f.write("def broken(\n    print('missing paren'")
        
    # 3. Missing MCP requirements
    with open("./seed_input/requirements.txt", "w") as f:
        f.write("requests==2.31.0\npillow>=10.0.0")

    # 4. Valid JSON
    with open("./seed_input/test_data.json", "w") as f:
        f.write('{"status": "testing", "value": 123}')

    # 5. Invalid JSON
    with open("./seed_input/corrupt_data.json", "w") as f:
        f.write('{"status": "broken", "value": 123')

    print("--- Test files ready! ---")

if __name__ == "__main__":
    setup_test_files()
