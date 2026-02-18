
import argparse
import sys
import subprocess
import os

def launch_interactive_ui(port):
    """Launch the Streamlit interactive UI."""
    print(f"--- [Bridge] Launching Interactive UI on port {port} ---")
    
    # Check if streamlit is installed
    try:
        import streamlit
    except ImportError:
        print("Error: Streamlit is not installed. Please run 'pip install streamlit'.")
        sys.exit(1)

    # Command to run streamlit
    cmd = [
        sys.executable, "-m", "streamlit", "run", "chat_ui.py",
        "--server.port", str(port),
        "--server.headless", "true"
    ]
    
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n--- [Bridge] UI Shutdown ---")
    except Exception as e:
        print(f"Error launching UI: {e}")

def main():
    parser = argparse.ArgumentParser(description="Creation Engine Bridge")
    parser.add_argument("--mode", type=str, choices=["interactive", "cli"], default="interactive", help="Operation mode")
    parser.add_argument("--ui-port", type=int, default=8501, help="Port for the interactive UI")

    args = parser.parse_args()

    if args.mode == "interactive":
        launch_interactive_ui(args.ui_port)
    elif args.mode == "cli":
        print("--- [Bridge] CLI Mode ---")
        # Could launch interactive_session.py here if needed
        # subprocess.run([sys.executable, "interactive_session.py"])
        print("CLI mode not fully integrated in this bridge script yet. Use 'python interactive_session.py' directly.")

if __name__ == "__main__":
    main()
