"""
Creation Engine — Configuration & Constants
All directives, platform profiles, package maps, and API conventions
extracted from the monolithic agent_brain.py into a clean module.
"""

import os

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
}
DEFAULT_PRICING = {"input": 0.002, "output": 0.006}


# ── Studio Mode Keywords ────────────────────────────────────
STUDIO_KEYWORDS = [
    "studio", "adobe", "photoshop", "editor", "graphics",
    "professional", "creative", "suite", "pro",
]
