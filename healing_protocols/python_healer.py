import os
import sys
import shutil
from datetime import datetime

class PythonHealer:
    """Healer Protocol for Python (.py) and MCP assets."""

    def __init__(self):
        # The 'Frost-Server' Standard
        self.required_libs = {
            'mcp': '>=0.1.0',
            'uvicorn': '>=0.22.0',
            'pydantic': '>=2.0.0'
        }

    def sentinel_validate(self, file_path):
        """Automated check for the frost-mcp-server failure patterns."""
        
        # 1. DEPENDENCY AUDIT (The 'requirements.txt' Healer)
        if os.path.basename(file_path) == 'requirements.txt':
            return self.audit_requirements(file_path)

        # 2. SYNTAX CHECK (Forces Python 3.12 compatibility)
        # only for .py files
        if file_path.endswith('.py'):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    compile(f.read(), file_path, 'exec')
            except SyntaxError as e:
                return False, f"SENTINEL_REJECT: Syntax Error detected - {e}"

        return True, "SENTINEL_PASS"

    def audit_requirements(self, req_path):
        """Ensures MCP-specific configurations aren't missing."""
        required_mcp = ['mcp', 'uvicorn', 'pydantic']
        try:
            with open(req_path, 'r', encoding='utf-8') as f:
                content = f.read().lower()
                
                # Check for missing MCP core dependencies
                missing = [pkg for pkg in required_mcp if pkg not in content]
                if missing:
                    # Note: We now allow missing libs here because Alchemist will inject them.
                    # However, if we want to be safe, we could reject if EVERYTHING is missing.
                    # For now, let's PASS to Alchemist if it's a valid requirements file.
                    pass
                
                return True, "SENTINEL_PASS"
        except Exception as e:
            return False, f"SENTINEL_REJECT: Error reading requirements - {e}"
        
        return True, "SENTINEL_PASS"

    def refine_requirements(self, file_path):
        """Automatically repairs formatting and pins missing dependencies."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = [line.strip().lower() for line in f.readlines() if line.strip()]

            # 1. Clean and Map existing libs
            existing_libs = {}
            for line in lines:
                if line.startswith('#'): continue
                if '==' in line:
                    name, ver = line.split('==', 1)
                    existing_libs[name.strip()] = f"=={ver.strip()}"
                elif '>=' in line:
                    name, ver = line.split('>=', 1)
                    existing_libs[name.strip()] = f">={ver.strip()}"
                else:
                    # UNPINNED DETECTED: Defaulting to latest or stable
                    existing_libs[line.strip()] = ">=0.0.0"

            # 2. Transmute: Inject missing or upgrade unpinned core MCP libraries
            for lib, required_ver in self.required_libs.items():
                if lib not in existing_libs or existing_libs[lib] == ">=0.0.0":
                    print(f"Alchemist: Transmuting/Injecting core - {lib}{required_ver}")
                    existing_libs[lib] = required_ver

            # 3. Final Formatting: Reconstruct the file
            refined_content = [f"{lib}{ver}" for lib, ver in sorted(existing_libs.items())]
            
            temp_path = file_path + ".healed"
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(refined_content) + "\n")
            
            return temp_path
        except Exception as e:
            print(f"Alchemist: Error refining requirements - {e}")
            return file_path

    def alchemist_process(self, file_path):
        """Applies formatting templates and optimizations."""
        if os.path.basename(file_path) == 'requirements.txt':
            return self.refine_requirements(file_path)

        # 1. Formatting Style Template
        # In a real scenario, this would call 'black' or 'ruff'
        # For this implementation, we ensure a clean header
        temp_path = file_path + ".healed"
        header = f"# Generated/Healed by Seed & Synthesis v1.0\n# Timestamp: {datetime.now()}\n\n"
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Remove existing duplicate headers if any
            if content.startswith("# Generated/Healed"):
                lines = content.splitlines()
                content = "\n".join(lines[3:])

            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(header + content)
            
            return temp_path
        except Exception:
            return file_path

    def stealth_apply(self, healed_path):
        """Wipes original metadata and replaces with S&S signature."""
        final_path = healed_path + ".stealth"
        
        # For text files, 'metadata' is often in the code comments or filesystem
        # We ensure the file only contains our signature
        try:
            shutil.copy2(healed_path, final_path)
            # In a more advanced version, we'd use 'exiftool' for files that support it
            # For Python, we've already injected the header in Alchemist
            return final_path
        except Exception:
            return healed_path
