import os
import shutil
import platform
import zipfile

from .llm_client import log

class OneHandoffPackager:
    """
    Handles final packaging for the 'One-Handoff' experience.
    Creates START_HERE.html, self-extracting archives (conceptually), 
    and organizes assets.
    """
    def __init__(self, project_path, project_name):
        self.project_path = project_path
        self.project_name = project_name
        self.output_dir = os.path.dirname(project_path)

    def create_package(self):
        log("PACKAGE", f"📦 Creating One-Handoff Package for {self.project_name}...")
        
        # 1. Apply Self-Healing Paths
        self._apply_self_healing()
        
        # 2. Generate START_HERE.html
        self._create_start_here()
        
        # 3. Bundle into Zip
        zip_path = os.path.join(self.output_dir, f"{self.project_name}_v1.0.zip")
        self._zip_project(zip_path)
        
        log("PACKAGE", f"✅ Package Ready: {zip_path}")
        return zip_path

    def _apply_self_healing(self):
        """Recursively replaces absolute paths with relative ones in all code files."""
        log("PACKAGE", "  🩹 Applying Self-Healing to asset paths...")
        abs_project_path = os.path.abspath(self.project_path).replace("\\", "/")
        
        # We look for any text file that might contain hardcoded absolute paths
        target_extensions = {".py", ".js", ".json", ".html", ".css", ".md", ".yaml", ".yml"}
        
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if any(file.endswith(ext) for ext in target_extensions):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        
                        # Replace absolute project root with relative dot
                        # Also handle double backslashes which common in Windows paths in code
                        fixed_path = abs_project_path
                        fixed_path_esc = fixed_path.replace("/", "\\\\")
                        
                        new_content = content.replace(abs_project_path, ".")
                        new_content = new_content.replace(fixed_path_esc, ".")
                        
                        if new_content != content:
                            with open(file_path, "w", encoding="utf-8") as f:
                                f.write(new_content)
                            log("PACKAGE", f"    ✓ Healed: {os.path.relpath(file_path, self.project_path)}")
                    except Exception as e:
                        log("WARN", f"    ⚠ Could not heal {file}: {e}")

    def _create_start_here(self):
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Start Here - {self.project_name}</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; background: #1a1a1a; color: #fff; padding: 40px; }}
        .container {{ max-width: 800px; margin: 0 auto; background: #2d2d2d; padding: 30px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }}
        h1 {{ color: #00bcd4; }}
        .btn {{ display: inline-block; padding: 10px 20px; background: #00bcd4; color: #000; text-decoration: none; border-radius: 5px; margin-top: 20px; font-weight: bold; }}
        .btn:hover {{ background: #00acc1; }}
        code {{ background: #000; padding: 2px 5px; border-radius: 3px; color: #0f0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Welcome to {self.project_name}</h1>
        <p>Your custom-built application is ready.</p>
        
        <h2>🚀 Quick Start</h2>
        <p>1. Open a terminal in this folder.</p>
        <p>2. Run the setup script:</p>
        <p><code>python setup.py</code> (if available) or <code>pip install -r requirements.txt</code></p>
        <p>3. Launch the application:</p>
        <p><code>python main.py</code></p>
        
        <h2>📂 Documentation</h2>
        <p>Refer to <code>README.md</code> for full details.</p>
        
        <a href="README.md" class="btn">Open Readme</a>
    </div>
</body>
</html>
"""
        with open(os.path.join(self.project_path, "START_HERE.html"), "w", encoding="utf-8") as f:
            f.write(html_content)
        log("PACKAGE", "  📄 Created START_HERE.html briefing.")

    def _zip_project(self, zip_path):
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(self.project_path):
                for file in files:
                    # Skip the zip itself if it's inside (unlikely but safe)
                    if file == os.path.basename(zip_path):
                        continue
                    # Skip __pycache__ etc
                    if "__pycache__" in root:
                        continue
                    
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, os.path.dirname(self.project_path))
                    zipf.write(file_path, arcname)
        log("PACKAGE", f"  🗜️  Compressed to {os.path.basename(zip_path)}")
