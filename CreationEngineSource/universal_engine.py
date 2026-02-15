#!/usr/bin/env python3
"""
Overlord - Universal Creation Engine (Modular Core Wrapper)
New Entry Point to bypass legacy agent_brain.py locks.
"""
import sys
import argparse
import os

# Add current directory to path so we can import 'core'
sys.path.append(os.getcwd())

# Load .env first
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass

try:
    from core.engine import CreationEngine
except ImportError as e:
    print(f"CRITICAL ERROR: Failed to import Creation Core: {e}")
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Universal Creation Engine")
    parser.add_argument("--project", required=True, help="Project name")
    parser.add_argument("--prompt", required=True, help="Prompt")
    parser.add_argument("--output", default="./output", help="Output directory")
    parser.add_argument("--model", default="gpt-4o", help="Model to use")
    
    args = parser.parse_known_args()[0]

    # Initialize Engine
    try:
        engine = CreationEngine(args.project, args.output, args.model)
        # Execute
        success = engine.run(args.prompt)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"CRITICAL ENGINE FAILURE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
