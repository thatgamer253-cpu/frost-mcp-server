#!/usr/bin/env python3
"""
=================================================================
  OVERLORD — One Handoff Create Command (Creation Engine)
  Usage:  python create.py "A personal finance app with CSV upload"
  
  This wrapper:
    1. Auto-generates a slug project name from your prompt
    2. Runs the Creation Engine pipeline (modular agents)
    3. Opens the output folder when done

  Falls back to legacy agent_brain.py if creation_engine unavailable.
=================================================================
"""
import os
import sys
import re
import subprocess
import platform

# Force UTF-8 mode for Windows consoles
if sys.platform == "win32":
    os.environ["PYTHONUTF8"] = "1"
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def slugify(text: str) -> str:
    """Convert a prompt into a clean project slug.
    'A personal finance app with CSV upload' → 'personal-finance-app'
    """
    stop_words = {"a", "an", "the", "with", "and", "or", "for", "to", "of", "in", "on", "by", "is", "it"}
    words = re.sub(r"[^a-zA-Z0-9\s]", "", text).lower().split()
    meaningful = [w for w in words if w not in stop_words][:6]
    slug = "-".join(meaningful) if meaningful else "overlord-project"
    return slug[:50]


def open_folder(path: str):
    """Open the output folder in the system file manager."""
    abs_path = os.path.abspath(path)
    system = platform.system()
    try:
        if system == "Windows":
            os.startfile(abs_path)
        elif system == "Darwin":
            subprocess.run(["open", abs_path], check=False)
        else:
            subprocess.run(["xdg-open", abs_path], check=False)
    except Exception:
        pass


def parse_args():
    """Parse CLI arguments. Returns (prompt, options_dict)."""
    if len(sys.argv) < 2:
        print("=" * 60)
        print("  OVERLORD — Creation Engine")
        print("=" * 60)
        print()
        print("  Usage:")
        print('    python create.py "Your project idea here"')
        print()
        print("  Options:")
        print("    --model <name>          Default model (default: gemini-2.0-flash)")
        print("    --arch-model <name>     Strategy model for Architect")
        print("    --eng-model <name>      Fast model for Developer")
        print("    --local-model <name>    Cheap model for Reviewer")
        print("    --review-model <name>   Senior review model")
        print("    --output <dir>          Output directory (default: ./output)")
        print("    --platform <name>       python|android|linux|studio")
        print("    --budget <amount>       Budget in USD (default: 5.0)")
        print("    --max-fix-cycles <n>    Max self-correction cycles (default: 3)")
        print("    --no-docker             Disable Docker sandbox")
        print("    --legacy                Force legacy agent_brain.py mode")
        print()
        print("  Examples:")
        print('    python create.py "A video streaming dashboard with user auth"')
        print('    python create.py "CLI tool for batch image resizing" --model llama3')
        print()
        sys.exit(1)

    prompt = None
    opts = {
        "model": "gemini-2.0-flash",
        "arch_model": None,
        "eng_model": None,
        "local_model": None,
        "review_model": None,
        "output": "./output",
        "platform": "python",
        "budget": 5.0,
        "max_fix_cycles": 3,
        "docker": True,
        "legacy": False,
        "scale": "auto",
        "local_only": False,
    }

    flag_map = {
        "--model": "model",
        "--arch-model": "arch_model",
        "--eng-model": "eng_model",
        "--local-model": "local_model",
        "--review-model": "review_model",
        "--output": "output",
        "--platform": "platform",
        "--budget": "budget",
        "--max-fix-cycles": "max_fix_cycles",
    }

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--no-docker":
            opts["docker"] = False
        elif arg == "--legacy":
            opts["legacy"] = True
        elif arg == "--local":
            opts["local_only"] = True
        elif arg in flag_map:
            if i + 1 < len(sys.argv):
                val = sys.argv[i + 1]
                key = flag_map[arg]
                if key in ("budget",):
                    opts[key] = float(val)
                elif key in ("max_fix_cycles",):
                    opts[key] = int(val)
                else:
                    opts[key] = val
                i += 1
        elif prompt is None:
            prompt = arg
        i += 1

    if not prompt:
        print("[ERROR] No prompt provided.")
        sys.exit(1)

    return prompt, opts


def run_creation_engine(prompt: str, project_name: str, opts: dict):
    """Run using the modular Creation Engine framework."""
    from creation_engine import CreationEngine

    engine = CreationEngine(
        project_name=project_name,
        prompt=prompt,
        output_dir=opts["output"],
        model=opts["model"],
        arch_model=opts["arch_model"],
        eng_model=opts["eng_model"],
        local_model=opts["local_model"],
        review_model=opts["review_model"],
        platform=opts["platform"],
        budget=opts["budget"],
        max_fix_cycles=opts["max_fix_cycles"],
        docker=opts["docker"],
        scale=opts["scale"],
        force_local=opts["local_only"],
    )

    result = engine.run()
    return result


def run_legacy(prompt: str, project_name: str, opts: dict):
    """Fallback: run the legacy agent_brain.py as a subprocess."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    brain_path = os.path.join(script_dir, "agent_brain.py")

    cmd = [
        sys.executable, brain_path,
        "--project", project_name,
        "--prompt", prompt,
        "--model", opts["model"],
        "--output", opts["output"],
        "--readme",
    ]

    if opts["docker"]:
        cmd.append("--docker")
    cmd.append("--debug")

    for flag, key in [("--arch-model", "arch_model"), ("--eng-model", "eng_model"),
                      ("--local-model", "local_model"), ("--review-model", "review_model")]:
        if opts.get(key):
            cmd.extend([flag, opts[key]])

    sub_env = os.environ.copy()
    sub_env["PYTHONUTF8"] = "1"
    sub_env["PYTHONIOENCODING"] = "utf-8"

    try:
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", bufsize=1, env=sub_env,
        )
        for line in process.stdout:
            print(line, end="")
        process.wait()
        return process.returncode == 0
    except KeyboardInterrupt:
        print("\n[ABORT] Build cancelled by user.")
        sys.exit(130)
    except Exception as e:
        print(f"[ERROR] Legacy build failed: {e}")
        return False


def main():
    prompt, opts = parse_args()
    project_name = slugify(prompt)

    print(f"\n{'=' * 60}")
    print(f"  >>> OVERLORD — Creation Engine")
    print(f"{'=' * 60}")
    print(f"  Project:  {project_name}")
    prompt_display = prompt[:80] + ('...' if len(prompt) > 80 else '')
    print(f"  Prompt:   {prompt_display}")
    print(f"  Model:    {opts['model']}")
    print(f"  Budget:   ${opts['budget']:.2f}")
    print(f"  Platform: {opts['platform']}")
    print(f"{'=' * 60}\n")

    project_path = os.path.join(opts["output"], project_name)
    success = False

    if opts["legacy"]:
        print("[MODE] Legacy (agent_brain.py subprocess)\n")
        success = run_legacy(prompt, project_name, opts)
    else:
        try:
            print("[MODE] Creation Engine (modular agents)\n")
            result = run_creation_engine(prompt, project_name, opts)
            success = result.get("success", False)
        except ImportError as e:
            print(f"[WARN] Creation Engine not available ({e}). Falling back to legacy mode.\n")
            success = run_legacy(prompt, project_name, opts)
        except KeyboardInterrupt:
            print("\n[ABORT] Build cancelled by user.")
            sys.exit(130)
        except Exception as e:
            print(f"[ERROR] Creation Engine crashed: {e}")
            print("[WARN] Falling back to legacy mode.\n")
            success = run_legacy(prompt, project_name, opts)

    # Open the output folder
    if success and os.path.isdir(project_path):
        print(f"\n{'=' * 60}")
        print(f"  ✅ BUILD COMPLETE")
        print(f"  Output: {os.path.abspath(project_path)}")
        print(f"{'=' * 60}\n")
        open_folder(project_path)
    else:
        print(f"\n{'=' * 60}")
        print(f"  ⚠ Build finished with issues")
        print(f"  Output: {os.path.abspath(project_path)}")
        print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
