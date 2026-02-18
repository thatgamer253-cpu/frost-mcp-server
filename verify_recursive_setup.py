import os

def setup_recursive_test():
    print("--- Setting up recursive test in ./output/nested_project ---")
    nested_path = "./output/nested_project/sub_module"
    os.makedirs(nested_path, exist_ok=True)
    
    # Unpinned requirements in a nested folder
    with open(os.path.join(nested_path, "requirements.txt"), "w") as f:
        f.write("flask\nmcp")

    print(f"--- Nested test file ready at {nested_path} ---")

if __name__ == "__main__":
    setup_recursive_test()
