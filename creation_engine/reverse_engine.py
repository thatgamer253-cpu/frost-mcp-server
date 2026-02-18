import os
from datetime import datetime

def log(tag, message):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [{tag}] {message}")

def reverse_engineering_agent(source_path):
    """
    Crawls source directory to build a structural map.
    Fulfills the 'Upgrade' mission by mapping what already exists.
    """
    log("REVERSE", f"🔍 Scanning source structure: {source_path}")
    source_map = {}

    for root, _, files in os.walk(source_path):
        for file in files:
            # Analyze logic-heavy files and manifests
            if file.endswith(('.py', '.js', '.ts', '.json', '.kts')):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, source_path)
                try:
                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        # Extract signatures: imports, classes, and functions
                        signatures = [line.strip() for line in content.split('\n') 
                                     if line.strip().startswith(('import ', 'from ', 'def ', 'class '))]
                        source_map[rel_path] = "\n".join(signatures)
                except Exception as e:
                    log("WARN", f"  Could not read {rel_path}: {e}")

    log("REVERSE", f"  ✓ Mapped {len(source_map)} files.")
    return source_map

if __name__ == "__main__":
    # Test run
    test_path = os.path.dirname(os.path.abspath(__file__))
    res = reverse_engineering_agent(test_path)
    print(f"Mapped {len(res)} files in local directory.")
