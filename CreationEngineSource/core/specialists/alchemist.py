import re
import os

class Alchemist:
    """
    The Alchemist (Code Purging & Refinement).
    Optimizes source code, removes AI artifacts, and ensures professional output.
    """

    def refine(self, file_path: str) -> bool:
        """Purges AI chatter and optimizes for professional-grade output."""
        print(f"[ALCHEMIST] Distilling {os.path.basename(file_path)}...")
        
        try:
            with open(file_path, 'r', encoding="utf-8") as f:
                raw_source = f.read()

            # 1. Remove Markdown Code Blocks (if mistakenly left in)
            clean = re.sub(r'^```[a-zA-Z]*\n', '', raw_source, flags=re.MULTILINE)
            clean = re.sub(r'\n```$', '', clean, flags=re.MULTILINE)

            # 2. Remove AI Chatter / Conversation Fillers
            clean = re.sub(r'# Certainly!.*', '', clean, flags=re.IGNORECASE)
            clean = re.sub(r'# Here is the.*', '', clean, flags=re.IGNORECASE)
            clean = re.sub(r'# I have updated.*', '', clean, flags=re.IGNORECASE)

            # 3. Strip massive blocks of empty lines
            clean = re.sub(r'\n{3,}', '\n\n', clean)
            
            clean = clean.strip()

            with open(file_path, 'w', encoding="utf-8") as f:
                f.write(clean)
            
            return True

        except Exception as e:
            print(f"[ALCHEMIST] [ERROR] Transmutation Failed: {e}")
            return False
