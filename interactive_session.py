
import os
import sys
import time
import json
import requests
from engine_core import NexusEngine
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.live import Live
from rich.spinner import Spinner
from rich.layout import Layout
from rich.align import Align
from rich import print as rprint

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass # dotenv not installed, using system env

# Configuration
OLLAMA_API_BASE = "http://localhost:11434/api"
DEFAULT_MODEL = "antigravity"
console = Console()

class AntigravitySession:
    def __init__(self):
        self.model = DEFAULT_MODEL
        self.context = []
        self.history = []

    def clear(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        self.print_banner()

    def print_banner(self):
        title = """
[bold magenta]ANTIGRAVITY CONSOLE[/bold magenta] [dim]v2.0[/dim]
[cyan]Powered by Ollama + Creation Engine[/cyan]
        """
        console.print(Panel(Align.center(title, vertical="middle"), style="bold white"))
        console.print("[dim]Type /help for commands. /build <prompt> to create software.[/dim]\n")

    def chat_stream(self, prompt):
        """Send chat request to Ollama and stream response."""
        url = f"{OLLAMA_API_BASE}/generate"
        data = {
            "model": self.model,
            "prompt": prompt,
            "context": self.context,
            "stream": True 
        }
        
        full_response = ""
        try:
            with requests.post(url, json=data, stream=True) as r:
                if r.status_code != 200:
                    console.print(f"[bold red]Error connecting to Ollama: {r.status_code}[/bold red]")
                    return

                # Create a Live display for streaming markdown
                with Live(Markdown(""), refresh_per_second=10, console=console) as live:
                    for line in r.iter_lines():
                        if line:
                            body = json.loads(line)
                            chunk = body.get("response", "")
                            full_response += chunk
                            live.update(Markdown(full_response))
                            
                            if body.get("done"):
                                self.context = body.get("context")
        except requests.exceptions.ConnectionError:
            console.print("[bold red]Connection failed. Is 'ollama serve' running?[/bold red]")

    def run_build(self, prompt):
        console.print(f"\n[bold green]🚀 INITIALIZING CREATION ENGINE[/bold green]")
        console.print(f"[dim]Goal: {prompt}[/dim]")
        
        try:
            engine = NexusEngine(
                project_name="", 
                model="ollama:llama3.2:3b", 
                output_dir="./output",
                use_docker=False 
            )
            
            with console.status("[bold cyan]Building software...[/bold cyan]", spinner="dots"):
                # We can't stream logs easily from here without engine modifications, 
                # but we can show it's working.
                result = engine.run_full_build(prompt)
            
            console.print(f"\n[bold green]✅ BUILD COMPLETE![/bold green]")
            console.print(f"[white]📂 Output Path:[/white] [link file://{result.get('project_path')}]{result.get('project_path')}[/link]")
            console.print(f"[dim]Files generated: {result.get('files_written', 0)}[/dim]")
            
        except Exception as e:
            console.print(f"\n[bold red]❌ Update Failed: {e}[/bold red]")

    def start(self):
        self.clear()
        
        while True:
            try:
                # Use Rich Prompt for better input handling
                user_input = Prompt.ask("\n[bold cyan]>>>[/bold cyan]")
                
                if not user_input.strip():
                    continue
                    
                command = user_input.split(" ")[0].lower()
                
                if command in ["/exit", "/quit", "/bye"]:
                    console.print("[yellow]👋 Disconnecting...[/yellow]")
                    break
                    
                elif command == "/clear":
                    self.clear()
                    self.context = [] 
                    continue

                elif command == "/help":
                    # ... (keep help)
                    help_text = """
[bold]Commands:[/bold]
  [green]/build <prompt>[/green]   Force build software
  [green]/model <name>[/green]     Switch model (current: [cyan]{}[/cyan])
  [green]/clear[/green]            Clear screen
  [green]/exit[/green]             Exit console
  
  [dim]Tip: You can just ask "Create a snake game" and I will try to build it![/dim]
                    """.format(self.model)
                    console.print(help_text)
                    continue
                    
                elif command == "/model":
                    parts = user_input.split(" ")
                    if len(parts) > 1:
                        self.model = parts[1]
                        console.print(f"[green]Set model to {self.model}[/green]")
                    else:
                        console.print(f"[yellow]Current model: {self.model}[/yellow]")
                    continue

                elif command == "/build":
                    prompt = user_input[7:].strip()
                    if not prompt:
                         console.print("[red]Usage: /build <what to build>[/red]")
                    else:
                        self.run_build(prompt)
                    continue

                # Smart Intent Detection - AUTO-BUILD
                lower_input = user_input.lower()
                build_keywords = ["create", "make", "build", "generate", "code", "program", "app", "script"]
                
                # Check for build intent + reasonable length
                if any(k in lower_input for k in build_keywords) and len(user_input.split()) > 2:
                    # Exclude questions or meta-discussion
                    if "how to" not in lower_input and "explain" not in lower_input and "what is" not in lower_input and "model" not in lower_input:
                        console.print(f"[bold yellow]🚀 Auto-Build Detected: '{user_input}'[/bold yellow]")
                        self.run_build(user_input)
                        continue

                # Default: Chat
                self.chat_stream(user_input)
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Use /exit to quit.[/yellow]")
            except Exception as e:
                console.print(f"[bold red]Error:[/bold red] {e}")

if __name__ == "__main__":
    session = AntigravitySession()
    session.start()
