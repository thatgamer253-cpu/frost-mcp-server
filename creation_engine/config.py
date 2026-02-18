"""
Creation Engine — Configuration & Constants
All directives, platform profiles, package maps, and API conventions
extracted from the monolithic agent_brain.py into a clean module.
"""

import os
import sys
import subprocess

# Windows-specific: suppress console windows for background processes
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

# ── Package Map ─────────────────────────────────────────────
# Mapping common import names to proper PyPI package names
PKG_MAP = {
    "PIL": "Pillow",
    "cv2": "opencv-python",
    "sklearn": "scikit-learn",
    "yaml": "PyYAML",
    "bs4": "beautifulsoup4",
    "dotenv": "python-dotenv",
    "ffmpeg": "ffmpeg-python",
    "googleapiclient": "google-api-python-client",
    "youtube_dl": "yt-dlp",
    "telegram": "python-telegram-bot",
    "gi": "PyGObject",
    "fal_client": "fal-client",
}


def _pypi_probe(import_name: str) -> str | None:
    """Query pip to check if a package name resolves on PyPI.
    Returns the canonical package name if found, else None."""
    # Common heuristics: try the import name as-is, then with 'python-' prefix
    candidates = [import_name, f"python-{import_name}", import_name.replace("_", "-")]
    for candidate in candidates:
        try:
            python_cmd = "python" if getattr(sys, 'frozen', False) else sys.executable
            r = subprocess.run(
                [python_cmd, "-m", "pip", "index", "versions", candidate],
                capture_output=True, text=True, timeout=10,
                creationflags=CREATE_NO_WINDOW
            )
            if r.returncode == 0 and candidate.lower() in r.stdout.lower():
                return candidate
        except Exception:
            continue
    return None


def resolve_package(import_name: str) -> str:
    """Resolve a Python import name to a PyPI package name.
    
    Strategy:
      1. Check static PKG_MAP (instant, no network)
      2. Fall back to live PyPI probe via `pip index`
      3. If both fail, return the import name as-is (best guess)
    """
    # 1. Static lookup
    if import_name in PKG_MAP:
        return PKG_MAP[import_name]
    
    # 2. Live PyPI probe
    resolved = _pypi_probe(import_name)
    if resolved:
        # Cache for future calls in this session
        PKG_MAP[import_name] = resolved
        return resolved
    
    # 3. Best guess: return as-is
    return import_name


# ── Production Safety Directive ─────────────────────────────
PRODUCTION_SAFETY_DIRECTIVE = (
    "\n\nPRODUCTION SAFETY INFRASTRUCTURE (MANDATORY for every project):"
    "\nEvery program you generate MUST include these safety pillars as core production code, not optional extras:"
    "\n\n1. HEALTH MONITORING:"
    "\n   - Python backends: add a /health endpoint returning JSON {status, uptime, version, checks:{db,cache,disk}}."
    "\n   - Long-running scripts: add a background health-check thread that logs system status every 60s."
    "\n   - Node apps: add a /api/health route with the same contract."
    "\n\n2. GRACEFUL ERROR RECOVERY:"
    "\n   - EVERY external call (DB, API, file I/O, network) MUST be wrapped in try-except."
    "\n   - On failure: log the error with context, return a safe fallback, NEVER crash the process."
    "\n   - Use specific exception types, not bare except. Always log traceback for unexpected errors."
    "\n\n3. SELF-HEALING & AUTO-REPAIR:"
    "\n   - Implement retry with exponential backoff for all network/DB operations (max 3 retries)."
    "\n   - Auto-reconnect database connections on pool exhaustion or timeout."
    "\n   - If a config file is missing, generate sensible defaults and log a warning."
    "\n   - Stale cache/lock detection: if a lock file is older than 5 minutes, auto-release it."
    "\n\n4. BACKUP & RESTORE:"
    "\n   - Before mutating any data file, create a .bak snapshot."
    "\n   - Use atomic writes (write to .tmp, then rename) for critical files."
    "\n   - Database operations: use transactions with rollback on failure."
    "\n\n5. WATCHDOG / SENTINEL:"
    "\n   - Add a background monitor thread that checks: disk space, memory usage, and process health."
    "\n   - If anomalies detected (disk >90%, memory >85%), log a WARNING and trigger cleanup."
    "\n   - For web servers: track response times and log slow endpoints (>2s)."
    "\n\n6. STRUCTURED LOGGING:"
    "\n   - Use a consistent logging format: [TIMESTAMP] [TAG] message."
    "\n   - Log every: startup, shutdown, error, recovery action, health check, and config change."
    "\n   - Include a startup banner that prints version, config source, and environment."
    "\n"
)


# ── Stability Directive ─────────────────────────────────────
STABILITY_DIRECTIVE = (
    "\n\nCODE STABILITY RULES (MANDATORY — violations will be REJECTED):"
    "\n1. CONFIG CONSISTENCY: When referencing config attributes (self.config.X, config.X, "
    "   app.config['X']), the attribute name MUST exactly match the attribute defined in the "
    "   Config/Settings class. Never invent config attributes that don't exist."
    "\n2. OPTIONAL PARAMETERS: All optional parameters must use 'Optional[Type] = None' "
    "   (from typing import Optional). Never write 'def foo(x: str = None)' — use "
    "   'def foo(x: Optional[str] = None)' instead."
    "\n3. IMPORT INTEGRITY: Only import symbols that are actually exported by the target "
    "   module. Check the project file tree — if importing 'from utils import helper', "
    "   the 'utils.py' file MUST define 'helper'. Never hallucinate import names."
    "\n4. ENUM CONSISTENCY: When referencing enum members, use the EXACT member name as "
    "   defined. If the enum defines 'status = \"active\"', reference it as Enum.status, "
    "   NOT Enum.STATUS or Enum.ACTIVE."
    "\n5. FONT PATHS: When using fonts (PIL, MoviePy, etc.), always use full file system "
    "   paths (e.g. 'C:/Windows/Fonts/arial.ttf'), never just font names like 'Arial'."
    "\n6. CROSS-FILE NAMING: Function, class, and variable names must be identical across "
    "   definition and all import sites. Never rename symbols at import boundaries."
    "\n"
)


# ── Feature Richness Directive ──────────────────────────────
FEATURE_RICHNESS_DIRECTIVE = (
    "\n\nFEATURE RICHNESS STANDARDS (MANDATORY — build impressive, not minimal):"
    "\n1. UI DEPTH: Every view must handle loading, empty, error, and success states. "
    "   Never leave a blank page — always show a skeleton, spinner, or empty-state illustration."
    "\n2. DATA TABLES: Any list/table MUST include: column sorting, search/filter bar, "
    "   pagination (10/25/50 per page), row selection with bulk actions, and CSV/JSON export."
    "\n3. VISUAL POLISH: Use CSS custom properties for theming. Include a dark/light mode "
    "   toggle. Add hover effects, focus rings, and smooth transitions (200-300ms ease)."
    "\n4. USER FEEDBACK: Every action (create, update, delete, submit) must show a toast "
    "   notification (success/error) and disable the submit button during processing."
    "\n5. DASHBOARD CARDS: Stat cards must show: value, label, trend indicator (▲/▼ with "
    "   percentage), and a subtle icon. Use a 2x2 or 3x1 grid layout."
    "\n6. FORMS: All forms must include field validation, helpful error messages, "
    "   placeholder text, and a reset/clear button alongside the submit button."
    "\n7. NAVIGATION: Include breadcrumbs on all sub-pages. Sidebar or top nav must show "
    "   active state. Add a user/settings menu in the header."
    "\n8. CHARTS: When displaying data trends, include at least 2 chart types "
    "   (line + bar, or pie + bar). Use a real charting library (Chart.js, Recharts, Plotly)."
    "\n9. SEED DATA: Generate realistic demo data (10-25 records) so the app looks alive "
    "   on first run. Never ship an empty database."
    "\n10. AUTO-REFRESH: Data views should poll for updates every 30s with a "
    "   'Last updated X ago' indicator. Include a manual refresh button."
    "\n"
)


# ── Portability & One-Click Readiness Directive ─────────────
PORTABILITY_DIRECTIVE = (
    "\n\nPORTABILITY & ONE-CLICK READINESS (MANDATORY):"
    "\nEvery program you generate MUST be 'one-click' ready for the user. "
    "Do NOT assume the user has dependencies pre-installed or a virtual environment active."
    "\n\n1. MANDATORY SETUP SCRIPTS:"
    "\n   - 'setup.ps1' (Windows): Automates venv creation, Pip upgrade, and 'pip install -r requirements.txt'."
    "\n     Include: 'Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process' at the top."
    "\n   - 'setup.sh' (Linux/macOS): Automates venv creation and dependency installation."
    "\n     Ensure it uses 'chmod +x' and specifies 'python3'."
    "\n\n2. BOOTSTRAP UTILITY:"
    "\n   - Include a 'bootstrap.py' or update 'main.py' to check for missing dependencies "
    "     at runtime and offer to install them or suggest running the setup script."
    "\n\n3. CLEAR DOCUMENTATION:"
    "\n   - The 'README.md' MUST start with a '🚀 Quick Start' section."
    "\n   - Provide the EXACT commands for Windows (Powershell) and Linux/macOS (Bash)."
    "\n   - State the minimum required Python version (default to 3.11+)."
    "\n\n4. PATH SAFETY:"
    "\n   - Use 'os.path' or 'pathlib' for all file operations. Never hardcode local paths "
    "     except for system fonts (using proper platform detection)."
    "\n"
)


# ── Standalone Distribution Directive ────────────────────────
DISTRIBUTION_DIRECTIVE = (
    "\n\nSTANDALONE DISTRIBUTION STANDARDS (MANDATORY):"
    "\nEvery program will be bundled into a single standalone .exe (Windows) or .app (macOS)."
    "\n\n1. ASSET PATH HANDLING:"
    "\n   - NEVER use relative paths like './assets/logo.png' directly in code."
    "\n   - ALWAYS use a resource path helper to handle bundled assets (PyInstaller/MEIPASS compatibility):"
    "\n     ```python"
    "\n     def get_resource_path(rel_path):"
    "\n         import sys, os"
    "\n         base_path = getattr(sys, '_MEIPASS', os.path.abspath('.'))"
    "\n         return os.path.join(base_path, rel_path)"
    "\n     ```"
    "\n\n2. DEPENDENCY HYGIENE:"
    "\n   - Do NOT use dynamic imports or code that requires a local Compiler/Shell (e.g. avoid 'gcc', 'go run')."
    "\n   - Only use libraries that are compatible with PyInstaller (standard pip packages)."
    "\n\n3. GUI CONFORMNACE:"
    "\n   - If the project is a GUI, it MUST not pop up a console window (use Window-friendly entry points)."
    "\n"
)


# ── API Conventions ─────────────────────────────────────────
API_CONVENTIONS = {
    "moviepy": (
        "MoviePy V2 API (MANDATORY): .subclip()->.subclipped(), "
        ".set_position()->.with_position(), .set_duration()->.with_duration(), "
        ".set_audio()->.with_audio(), .set_start()->.with_start(), "
        ".set_end()->.with_end(), .set_opacity()->.with_opacity(), "
        ".set_fps()->.with_fps(), .volumex()->.with_volume_scaled(), "
        ".resize()->.resized(), .crop()->.cropped(), .rotate()->.rotated(). "
        "TextClip: first arg is 'font' (full .ttf path), 'text' is keyword-only, use 'font_size' not 'fontsize'. "
        "Imports: use 'from moviepy import X', NOT 'from moviepy.editor import X'. "
        "Resizing: use .resized(new_size=(...)), NOT .resized(newsize=(...))."
    ),
    "pydantic": (
        "Pydantic V2 API: Use 'field_validator' not 'validator', 'model_config = ConfigDict(...)' "
        "not 'class Config:', '.model_dump()' not '.dict()', 'model_json_schema()' not '.schema()'. "
        "BaseSettings moved to 'pydantic-settings' package."
    ),
    "flask": (
        "Flask 2.3+ REMOVED @app.before_first_request. Use direct function calls during "
        "app init instead. Use 'app.config[ATTR]' where ATTR matches the Config class attribute name exactly."
    ),
    "fastapi": (
        "FastAPI: Pin both 'fastapi' and 'pydantic' versions in requirements.txt. "
        "If using Pydantic V2, apply all V2 patterns (field_validator, ConfigDict, model_dump)."
    ),
    "pillow": (
        "Pillow/PIL: When specifying fonts, use full file system paths to .ttf files "
        "(e.g. 'C:/Windows/Fonts/arial.ttf'), not font names. ImageFont.truetype() requires a file path."
    ),
}


# ── Platform Profiles ───────────────────────────────────────
PLATFORM_PROFILES = {
    "python": {
        "label": "🐍 Python (Default)",
        "arch_directive": (
            "Target: Standard Python application. "
            "Use Python 3.11+ with pip for dependencies. "
            "Entry point: main.py. Package manager: requirements.txt. "
            "Docker base: python:3.12-slim."
        ),
        "file_extensions": [".py"],
        "run_command": "python main.py",
        "build_command": "pip install -r requirements.txt",
        "docker_base": "python:3.12-slim",
        "dep_file": "requirements.txt",
    },
    "android": {
        "label": "🤖 Android (Kotlin + Gradle)",
        "arch_directive": (
            "Target: Native Android application using Kotlin and Jetpack Compose. "
            "Project structure MUST follow standard Android/Gradle layout: "
            "app/src/main/java/com/<package>/ for Kotlin sources, "
            "app/src/main/res/ for resources (layout, values, drawable), "
            "app/src/main/AndroidManifest.xml for the manifest. "
            "Root files: build.gradle.kts (project), app/build.gradle.kts (module), "
            "settings.gradle.kts, gradle.properties. "
            "Use Material 3 design components. Min SDK 24, target SDK 34. "
            "Use Kotlin coroutines for async. Use Retrofit for networking. "
            "Use Hilt for dependency injection. Use Room for local database. "
            "Do NOT include requirements.txt or Dockerfile — use Gradle only. "
            "The run_command should be: ./gradlew assembleDebug"
        ),
        "file_extensions": [".kt", ".xml", ".kts"],
        "run_command": "./gradlew assembleDebug",
        "build_command": "./gradlew build",
        "docker_base": "thyrlian/android-sdk:latest",
        "dep_file": "app/build.gradle.kts",
    },
    "linux": {
        "label": "🐧 Linux Desktop (Python + GTK/Qt)",
        "arch_directive": (
            "Target: Native Linux desktop application. "
            "Use Python 3.11+ with either PyGObject (GTK4) or PyQt6 for the GUI. "
            "Include a .desktop file for XDG menu integration. "
            "Include an install.sh script that installs system deps via apt/dnf. "
            "Include an AppImage or Flatpak manifest if appropriate. "
            "Entry point: main.py. Package manager: requirements.txt + system deps. "
            "Use Meson or setuptools for packaging. "
            "Follow Freedesktop.org standards for icons and .desktop files. "
            "Docker base: python:3.12-slim (for testing). "
            "The run_command should be: python3 main.py"
        ),
        "file_extensions": [".py", ".desktop", ".sh"],
        "run_command": "python3 main.py",
        "build_command": "pip install -r requirements.txt",
        "docker_base": "python:3.12-slim",
        "dep_file": "requirements.txt",
    },
    "studio": {
        "label": "🎨 Studio Engine (High Performance)",
        "arch_directive": (
            "Target: Professional-grade Creative Suite Application. "
            "Use PyQt6 for a robust, multi-threaded GUI with Dock Widgets, Toolbars, and Menus. "
            "Mandatory Libraries: PyQt6 (UI), NumPy (Processing), OpenCV (Vision/Image Processing). "
            "Architecture: Modular/Plugin-based. Create a 'core/' folder for the engine and 'plugins/' for effects. "
            "Use multi-threading (QThread) to keep the UI responsive during heavy processing. "
            "Entry point: app.py. The program MUST run immediately with no missing assets. "
            "If custom icons or cursors are needed, generate them using the MediaEngine."
        ),
        "file_extensions": [".py", ".ui", ".qrc"],
        "run_command": "python app.py",
        "build_command": "pip install PyQt6 opencv-python numpy",
        "docker_base": "python:3.12-slim",
        "dep_file": "requirements.txt",
    },
    # ── Media & Production (Asset-Centric) ───────────────
    "movie": {
        "label": "🎬 Movie / Cinematic Video",
        "arch_directive": "TARGET: Cinematic Video Asset. Use the MediaEngine to generate a high-quality video file based on the prompt. Do NOT generate code.",
        "file_extensions": [".mp4", ".mov"],
        "run_command": "echo 'Asset Ready'",
        "build_command": "echo 'Rendering...'",
        "docker_base": "python:3.12-slim",
    },
    "music": {
        "label": "🎵 Music / Audio Track",
        "arch_directive": "TARGET: Audio Asset. Use the MediaEngine to generate music or audio tracks. Do NOT generate code.",
        "file_extensions": [".mp3", ".wav"],
        "run_command": "echo 'Asset Ready'",
        "build_command": "echo 'Synthesizing...'",
        "docker_base": "python:3.12-slim",
    },
    "media-asset": {
        "label": "🎨 Digital Media Asset",
        "arch_directive": "TARGET: Visual Asset (Image/Graphic). Use the MediaEngine for generation. Do NOT generate code.",
        "file_extensions": [".png", ".jpg", ".svg"],
        "run_command": "echo 'Asset Ready'",
        "build_command": "echo 'Generating...'",
        "docker_base": "python:3.12-slim",
    },
}



# ── Design System Archetypes (The "Vibe") ───────────────────
DESIGN_ARCHETYPES = {
    "3d_interactive_space": {
        "keywords": ["3d", "three.js", "r3f", "webgl", "immersive", "museum", "virtual world", "spatial"],
        "stack_additions": ["three", "@react-three/fiber", "@react-three/drei", "framer-motion-3d"],
        "ui_directive": (
            "DESIGN CHEAT CODE: 'Virtual Museum'. \n"
            "The user wants a 3D INTERACTIVE SPACE. \n"
            "1. USE: React Three Fiber for the main canvas. \n"
            "2. NAV: Camera movements (OrbitControls, FlyControls) instead of scroll. \n"
            "3. STYLE: Dark void backgrounds, neon accents, floating 3D icons. \n"
            "4. INTERACTION: Raycasting for clicks. 'Enter' functionality to move between scenes."
        )
    },
    "emotional_playful_ui": {
        "keywords": ["emotional", "playful", "fun", "cute", "whimsical", "bouncy", "wufoo", "joy"],
        "stack_additions": ["framer-motion", "canvas-confetti", "react-use-measure"],
        "ui_directive": (
            "DESIGN CHEAT CODE: 'Joyful Bounce'. \n"
            "The user wants an EMOTIONAL, PLAYFUL interface (Wufoo style). \n"
            "1. COPY: Use humor, informal tone, and enthusiastic success messages. \n"
            "2. ANIMATION: Everything must bounce, pop, or slide. Use Framer Motion 'spring' config. \n"
            "3. COLOR: High saturation, rounded corners (borderRadius: '32px'), chunky borders. \n"
            "4. INPUTS: Large, friendly inputs. 'Mad Libs' style forms."
        )
    },
    "gamified_workflow": {
        "keywords": ["gamified", "game", "tetris", "points", "score", "level up", "leaderboard", "matching"],
        "stack_additions": ["framer-motion", "react-beautiful-dnd", "zustand"],
        "ui_directive": (
            "DESIGN CHEAT CODE: 'Tetris workflow'. \n"
            "The user wants to GAMIFY a boring task (accounting, data entry). \n"
            "1. MECHANIC: Turn tasks into 'matching' games or 'clearing lines'. \n"
            "2. REWARD: Visual confetti/particles on every completion. XP progress bars. \n"
            "3. SOUND: Add subtle SFX for interactions (use Web Audio API). \n"
            "4. LAYOUT: Game HUD style (score top right, inventory bottom)."
        )
    },
    "mobile_card_wrap": {
        "keywords": ["cards", "swipe", "stories", "tiktok", "reel", "wrap", "mobile", "sms", "instagram"],
        "stack_additions": ["framer-motion", "swiper", "react-use-gesture"],
        "ui_directive": (
            "DESIGN CHEAT CODE: 'Swipe Stories' (Instagram/TikTok style). \n"
            "The user wants a MOBILE-FIRST CARD interface. \n"
            "1. LAYOUT: Full-screen vertical cards. 100vh height. \n"
            "2. NAV: Swipe up/down/left/right. No scrollbars. \n"
            "3. STYLE: Instagram Gradients (Purple/Orange/Pink). Glassmorphism overlays. \n"
            "4. CONTENT: Big typography, background images/video, minimal text per card."
        )
    },
    "gradient_animated_flow": {
        "keywords": ["gradient", "flow", "animated", "fluid", "mesh", "aurora", "stripe", "spotify"],
        "stack_additions": ["whatamesh", "framer-motion"],
        "ui_directive": (
            "DESIGN CHEAT CODE: 'Liquid Aurora'. \n"
            "The user wants a VISUALLY STUNNING GRADIENT background. \n"
            "1. BG: Animated mesh gradients or slow-moving colors. \n"
            "2. GLASS: Use backdrop-filter: blur(20px) for cards/overlays. \n"
            "3. TEXT: Big, bold, white text on dark, shifting backgrounds. \n"
            "4. FEELING: Ethereal, premium, fluid."
        )
    },
    "minimalist_punch": {
        "keywords": ["minimalist", "clean", "Swiss", "brutalist", "simple", "whitespace", "x", "twitter"],
        "stack_additions": [],
        "ui_directive": (
            "DESIGN CHEAT CODE: 'X / Twitter Stark'. \n"
            "The user wants EXTREME MINIMALISM / BRUTALISM. \n"
            "1. COLOR: Stark Black & White (X style) or Monochrome. \n"
            "2. SPACE: Double all margins/padding. \n"
            "3. TYPE: Huge headings. Monospace for data. \n"
            "4. BORDERS: 1px solid dividers. No shadows. Flat design."
        )
    },
    "youtube_studio_red": {
        "keywords": ["youtube", "video platform", "streaming", "red", "studio"],
        "stack_additions": ["recharts", "react-player"],
        "ui_directive": (
            "DESIGN CHEAT CODE: 'YouTube Studio Red'. \n"
            "The user wants a VIDEO PLATFORM aesthetic. \n"
            "1. COLOR: Dark Mode Background (#0F0F0F) with YouTube Red (#FF0000) accents. \n"
            "2. LAYOUT: Sidebar navigation + Main Content Grid. \n"
            "3. COMPONENTS: Video thumbnails with duration badges. Analytics charts. \n"
            "4. TYPOGRAPHY: Roboto or consistent Sans-Serif."
        )
    },
}


# ── Layout Templates (The "Structure") ──────────────────────
LAYOUT_TEMPLATES = {
    "accordion_museum": {
        "keywords": ["accordion", "slide", "museum", "gallery", "sections", "horizontal"],
        "description": "Horizontal accordion menu where sections expand to reveal content. Good for storytelling.",
    },
    "bento_grid": {
        "keywords": ["bento", "grid", "masonry", "dashboard", "cards", "modular", "blocks"],
        "description": "Responsive masonry grid (3-column) with variable-height cards. (Apple/Linear style).",
    },
    "focus_canvas": {
        "keywords": ["canvas", "focus", "editor", "ide", "workspace", "center", "youtube"],
        "description": "Central workspace/player with collapsible sidebars (left/right). (YouTube Studio / VS Code style).",
    },
    "feed_stream": {
        "keywords": ["feed", "stream", "social", "timeline", "scrolling", "posts", "x", "twitter"],
        "description": "Infinite-scroll central column with sticky utilization sidebars. (X / Twitter style).",
    },
    "mobile_stack": {
        "keywords": ["mobile", "app", "stack", "phone", "pocket"],
        "description": "Single-column stack with bottom navigation bar and pull-to-refresh.",
    },
}


# ── LLM Providers ───────────────────────────────────────────
PROVIDERS = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "env_key": "GROQ_API_KEY",
        "prefixes": ["llama", "gemma", "mixtral"],
        "label": "Groq ⚡ (FREE)",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "env_key": "GEMINI_API_KEY",
        "prefixes": ["gemini"],
        "label": "Google Gemini 🧠 (FREE)",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "env_key": "OPENROUTER_API_KEY",
        "prefixes": ["openrouter/", "meta-llama/", "google/", "mistralai/", "deepseek/"],
        "label": "OpenRouter 🌐 (FREE tier)",
    },
    "openai": {
        "base_url": None,
        "env_key": "OPENAI_API_KEY",
        "prefixes": ["gpt-", "o1-", "o3-"],
        "label": "OpenAI ☁️",
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com",
        "env_key": "ANTHROPIC_API_KEY",
        "prefixes": ["claude"],
        "label": "Anthropic 🔒 (Reviewer)",
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "env_key": "OLLAMA_API_KEY",  # Dummy key, usually not needed but good for compatibility
        "prefixes": ["local/", "ollama", "llama", "mistral", "gemma", "phi"],
        "label": "Ollama 🦙 (Local)",
    },
}


# ── Cost Pricing Table ──────────────────────────────────────
PRICING = {
    "gpt-4o":               {"input": 0.0025, "output": 0.010},
    "gpt-4o-mini":          {"input": 0.00015, "output": 0.0006},
    "gpt-4-turbo":          {"input": 0.01,   "output": 0.03},
    "gpt-3.5-turbo":        {"input": 0.0005, "output": 0.0015},
    "o1":                   {"input": 0.015,  "output": 0.06},
    "o1-mini":              {"input": 0.003,  "output": 0.012},
    "gemini-2.0-flash":     {"input": 0.0001, "output": 0.0004},
    "gemini-1.5-pro":       {"input": 0.00125,"output": 0.005},
    "llama3-70b-8192":      {"input": 0.00059,"output": 0.00079},
    "llama3-8b-8192":       {"input": 0.00005,"output": 0.00008},
    "mixtral-8x7b-32768":   {"input": 0.00024,"output": 0.00024},
    "llama3":               {"input": 0.0,    "output": 0.0},
    "codellama":            {"input": 0.0,    "output": 0.0},
    "mistral":              {"input": 0.0,    "output": 0.0},
    "ollama":               {"input": 0.0,    "output": 0.0},
}
DEFAULT_PRICING = {"input": 0.002, "output": 0.006}


# ── Studio Mode Keywords ────────────────────────────────────
STUDIO_KEYWORDS = [
    "studio", "adobe", "photoshop", "editor", "graphics",
    "professional", "creative", "suite", "pro",
]

# ── Directives (Defaults) ───────────────────────────────────
def get_all_directives():
    """Load current directives (potentially overridden)."""
    try:
        from .settings import load_settings
        return load_settings()["directives"]
    except ImportError:
        return {
            "safety": PRODUCTION_SAFETY_DIRECTIVE,
            "stability": STABILITY_DIRECTIVE,
            "richness": FEATURE_RICHNESS_DIRECTIVE,
            "portability": PORTABILITY_DIRECTIVE,
            "distribution": DISTRIBUTION_DIRECTIVE,
        }
