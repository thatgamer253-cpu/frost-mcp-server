import os
import logging
import json
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s')

class NexusDecompiler:
    """
    Nexus Decompiler Module.
    Digests existing programs into modular instructions, documentation, and architectural overviews.
    """

    @staticmethod
    def extract_code_from_directory(directory: str) -> List[str]:
        """Extract all Python source code files from the specified directory."""
        code_files = []
        try:
            for root, _, files in os.walk(directory):
                # Skip common ignore dirs
                if any(x in root for x in ['venv', '.git', '__pycache__', 'node_modules']):
                    continue
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        code_files.append(file_path)
        except Exception as e:
            logging.error(f"Error extracting code from directory {directory}: {e}")
        return code_files

    @staticmethod
    def analyze_code(file_path: str) -> Dict[str, Any]:
        """Analyze a Python source code file and extract relevant information."""
        analysis_results = {
            "functions": [],
            "classes": [],
            "imports": []
        }
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                lines = file.readlines()
                for line in lines:
                    line = line.strip()
                    if line.startswith('def '):
                        function_name = line.split('(')[0][4:].strip()
                        analysis_results["functions"].append(function_name)
                    elif line.startswith('class '):
                        class_name = line.split('(')[0][6:].split(':')[0].strip()
                        analysis_results["classes"].append(class_name)
                    elif line.startswith('import ') or line.startswith('from '):
                        analysis_results["imports"].append(line)
        except Exception as e:
            logging.error(f"Error analyzing code file {file_path}: {e}")
        return analysis_results

    def digest_project(self, directory: str) -> Dict[str, Any]:
        """
        Perform a full digestion of a project directory.
        Returns a dictionary containing the extracted instructions and structure.
        """
        code_files = self.extract_code_from_directory(directory)
        analysis_summary = {}
        
        for cf in code_files:
            rel_path = os.path.relpath(cf, directory)
            analysis_summary[rel_path] = self.analyze_code(cf)
            
        # Generate Architectural Overview
        arch_overview = self.generate_architecture_overview(analysis_summary)
        
        # Generate Documentation
        docs = self.generate_documentation(os.path.basename(directory), analysis_summary)
        
        return {
            "project_name": os.path.basename(directory),
            "files_found": len(code_files),
            "analysis": analysis_summary,
            "architecture": arch_overview,
            "documentation": docs
        }

    @staticmethod
    def generate_llm_context(directory: str, max_chars: int = 100000) -> str:
        """
        Generate a single string containing the project's source code,
        formatted for ingestion by an LLM (XML-like tags).
        Includes a file tree and content of non-ignored files.
        """
        context = []
        context.append(f"Project: {os.path.basename(directory)}\n")
        
        # 1. File Tree
        context.append("### File Tree")
        files_list = []
        for root, _, files in os.walk(directory):
            if any(x in root for x in ['venv', '.git', '__pycache__', 'node_modules', 'dist', 'build', '.idea', '.vscode']):
                continue
            for file in files:
                if file.endswith(('.pyc', '.pyo', '.pyd', '.db', '.sqlite', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.zip', '.tar', '.gz')):
                    continue
                path = os.path.join(root, file)
                rel_path = os.path.relpath(path, directory)
                files_list.append(rel_path)
                context.append(f"- {rel_path}")
        context.append("")

        # 2. File Contents
        context.append("### Source Code")
        char_count = 0
        
        for rel_path in files_list:
             # Skip really large files or lock files
            if "lock" in rel_path or "json" in rel_path: # simplistic filter
                continue
                
            full_path = os.path.join(directory, rel_path)
            try:
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                # Basic context limit check
                if char_count + len(content) > max_chars:
                    context.append(f"\n[... Truncated remaining files due to size limit ...]")
                    break
                    
                context.append(f"\n<file path=\"{rel_path}\">")
                context.append(content)
                context.append("</file>")
                char_count += len(content)
            except Exception as e:
                context.append(f"\n<file path=\"{rel_path}\" error=\"{str(e)}\" />")

        return "\n".join(context)

    @staticmethod
    def generate_architecture_overview(analysis_results: Dict[str, Any]) -> str:
        """Generate a textual overview of the architecture."""
        overview = ["# Nexus Architectural Overview\n"]
        for file, data in analysis_results.items():
            overview.append(f"### {file}")
            if data["classes"]:
                overview.append(f"- **Classes**: {', '.join(data['classes'])}")
            if data["functions"]:
                overview.append(f"- **Functions**: {', '.join(data['functions'])}")
            overview.append("")
        return "\n".join(overview)

    @staticmethod
    def generate_documentation(project_name: str, analysis_results: Dict[str, Any]) -> str:
        """Generate markdown documentation for the project."""
        docs = [f"# Documentation for {project_name}\n"]
        docs.append("## Project Summary")
        docs.append(f"Auto-generated by Nexus Decompiler. Total modules analyzed: {len(analysis_results)}.\n")
        
        docs.append("## Module Breakdown")
        for file, data in analysis_results.items():
            docs.append(f"### `{file}`")
            if data["classes"]:
                docs.append("#### Classes")
                for c in data["classes"]: docs.append(f"- `{c}`")
            if data["functions"]:
                docs.append("#### Functions")
                for f in data["functions"]: docs.append(f"- `{f}`")
            docs.append("")
        return "\n".join(docs)
