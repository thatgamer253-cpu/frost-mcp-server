import os
import shutil
import tempfile
import sys
from api_migrator import Migrator

def test_migration_roundtrip():
    """Verify that migration works and revert works."""
    with tempfile.TemporaryDirectory() as td:
        project_dir = os.path.join(td, "legacy_project")
        os.makedirs(project_dir)
        
        # 1. Create legacy files
        app_py = os.path.join(project_dir, "app.py")
        with open(app_py, "w") as f:
            f.write('''#!/usr/bin/env python3
"""A legacy app."""
import openai

API_KEY = "sk-12345678901234567890123456789012"
client = openai.OpenAI(api_key=API_KEY)

def talk():
    return client.chat.completions.create(model="gpt-4", messages=[])
''')

        # 2. Run Migrator (Apply)
        print("--- Running Migration (Apply) ---")
        migrator = Migrator(project_dir, dry_run=False)
        migrator.scan_and_refactor()
        
        # 3. Verify results
        with open(app_py, "r") as f:
            content = f.read()
            print(f"Refactored app.py:\n{content}")
            assert "os.environ.get('OPENAI_API_KEY')" in content
            assert "get_cached_client('auto')" in content
            assert "from creation_engine.llm_client import" in content
            
        env_path = os.path.join(project_dir, ".env")
        assert os.path.exists(env_path)
        with open(env_path, "r") as f:
            env_content = f.read()
            print(f"Generated .env:\n{env_content}")
            assert "OPENAI_API_KEY=sk-12345678901234567890123456789012" in env_content

        # 4. Verify Revert
        print("--- Running Revert ---")
        migrator.revert()
        with open(app_py, "r") as f:
            content = f.read()
            assert "sk-12345678901234567890123456789012" in content
            assert "OpenAI(api_key=API_KEY)" in content
        
        print("\n✅ API Migrator Test: PASSED")

if __name__ == "__main__":
    try:
        test_migration_roundtrip()
    except Exception as e:
        print(f"\n❌ API Migrator Test: FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
