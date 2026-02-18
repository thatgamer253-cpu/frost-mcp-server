"""
Creation Engine — Stealth & Privacy Engine
Scans and scrubs sensitive local data (usernames, paths, IPs) before production.
"""

import re
import os

class StealthEngine:
    def __init__(self):
        # Patterns to scrub: Usernames, Local Windows/Mac Paths, and IPs
        self.sensitive_patterns = [
            r"C:/Users/[^/]+",            # Windows User Paths
            r"/Users/[^/]+",              # Mac/Linux User Paths
            r"thatgamer253[-a-zA-Z0-9]*",   # Common usernames
            r"Donovan",                   # Personal Name
            r"192\.168\.\d+\.\d+",        # Local IP Addresses
        ]
        self.replacement = "[REDACTED_CORE_PATH]"

    def scrub_content(self, file_path, output_dir="./synthesis_final/"):
        """Removes local identifiers and anonymizes the file."""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # 1. SCRUB PERSONAL STRINGS
        for pattern in self.sensitive_patterns:
            content = re.sub(pattern, self.replacement, content, flags=re.IGNORECASE)

        # 2. ANONYMIZE COMMENTS
        # Replaces developer-specific comments with engine-standard ones
        content = re.sub(r"# Created by .*", "# Source: Seed & Synthesis Autonomous Engine", content)

        # 3. SAVE TO FINAL DESTINATION
        # Moves file from 'Healed' to 'Live' folder
        final_filename = os.path.basename(file_path)
        final_path = os.path.join(output_dir, final_filename)
        
        with open(final_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        return final_path
