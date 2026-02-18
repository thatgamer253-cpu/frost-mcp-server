import os

def setup_repair_test():
    print("--- Setting up unpinned requirements.txt in ./seed_input ---")
    os.makedirs("./seed_input", exist_ok=True)
    
    # Unpinned requirements (should be healed by Alchemist)
    with open("./seed_input/requirements.txt", "w") as f:
        f.write("requests\npillow\nmcp") # 'mcp' is present but unpinned, 'uvicorn' and 'pydantic' are missing

    print("--- Test file ready! ---")

if __name__ == "__main__":
    setup_repair_test()
