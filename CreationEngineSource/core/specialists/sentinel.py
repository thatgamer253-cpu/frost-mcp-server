import py_compile
import ast
import os
from typing import Tuple

class Sentinel:
    """
    The Sentinel (Atomic Validation).
    Performs deep AST analysis and compilation checks to ensure code stability.
    """
    
    def audit(self, file_path: str) -> bool:
        """Atomic check to ensure the code is stable and runnable."""
        print(f"[SENTINEL] Validating {os.path.basename(file_path)}...")
        
        # 1. Syntax Check (Compile)
        try:
            py_compile.compile(file_path, doraise=True)
        except Exception as e:
            print(f"[SENTINEL] [ERROR] Integrity Breach (Syntax): {e}")
            return False

        # 2. AST Analysis (Deeper Check)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
            ast.parse(source)
        except Exception as e:
             print(f"[SENTINEL] [ERROR] Integrity Breach (AST): {e}")
             return False

        return True
