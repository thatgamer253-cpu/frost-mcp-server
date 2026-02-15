"""
Creation Engine — Architect Agent
Handles Phase 0 (Prompt Enhancement) and Phase 1 (Blueprint Generation).
Produces a JSON manifest: project_name, stack, file_tree, files, dependencies, run_command.
"""

import json

from .config import (
    PRODUCTION_SAFETY_DIRECTIVE,
    PLATFORM_PROFILES,
    STUDIO_KEYWORDS,
)
from .llm_client import log, divider, ask_llm


# ── Prompt Enhancer (Phase 0) ───────────────────────────────

def enhance_prompt(client, model: str, raw_prompt: str, platform_directive: str, scale: str = "app") -> str:
    """Transform a brief user idea into a rich engineering specification."""

    enhance_system = (
        "You are 'Overlord Prompt Engineer,' an elite AI that transforms vague user ideas "
        "into detailed, comprehensive software engineering specifications. "
        "The user will give you a brief idea — maybe just a few words. "
        "Your job is to expand it into a RICH, AMBITIOUS prompt that a code-generating AI can use to build "
        "a complete, production-quality, feature-packed application. "
        "Think like a Product Manager at a top tech company — the goal is to IMPRESS, not just function. "
        f"\n\nPLATFORM CONSTRAINT: {platform_directive} "
        "\n\nYour enhanced prompt MUST include ALL of these categories:"
        "\n\n📋 CATEGORY 1 — CORE FEATURES (3-5 features):"
        "\n  The primary business logic and main functionality the app must deliver."
        "\n\n📊 CATEGORY 2 — DATA MANAGEMENT (3-4 features):"
        "\n  Search with filters, sortable columns, pagination, data export (CSV/JSON), "
        "  bulk actions (select all, bulk delete), and import capabilities."
        "\n\n🎨 CATEGORY 3 — UI/UX EXCELLENCE (3-4 features):"
        "\n  Responsive layout (mobile + desktop), dark/light mode toggle, loading skeletons, "
        "  toast notifications for all actions, empty-state illustrations, breadcrumb navigation, "
        "  sidebar or top nav with active states, and smooth CSS transitions/animations."
        "\n\n📈 CATEGORY 4 — ANALYTICS & DASHBOARDS (2-3 features):"
        "\n  Stats cards with trend indicators (▲/▼), at least 2 chart types (bar, line, pie, or gauge), "
        "  activity feed or recent-actions log, and summary metrics on the main page."
        "\n\n⚡ CATEGORY 5 — REAL-TIME & PERFORMANCE (1-2 features):"
        "\n  Auto-refresh with polling interval, 'Last updated X ago' indicators, "
        "  optimistic UI updates, and caching where appropriate."
        "\n\n🔧 CATEGORY 6 — SETTINGS & CONFIGURATION (1-2 features):"
        "\n  User preferences panel, environment-based config (.env), "
        "  and a seed/demo data command so the app looks alive on first run."
        "\n\nThe result should specify 12-20 concrete features total across these categories."
        "\n\nRules:"
        "\n- Output ONLY the enhanced prompt text. No markdown, no headers, no explanations."
        "\n- Write it as a single, flowing engineering specification."
        "\n- Be specific — name exact function names, exact UI elements, exact data structures."
        "\n- If the idea involves media, include image/video generation capabilities."
        "\n- Always include a main entry point and a proper CLI or GUI."
        "\n- Make it sound like a Product Requirements Document from a senior PM."
        "\n- Target 600-800 words. Make every word count."
    )

    if scale == "script":
        enhance_system = (
            "You are 'Overlord Zero-Bloat Architect.' Transform user ideas into a TIGHT, "
            "LOGIC-ONLY engineering specification for a STANDALONE SCRIPT. "
            "Ignore UI, ignore analytics, ignore monitoring. Focus on the core algorithm, "
            "data processing, and CLI input/output. "
            f"\n\nPLATFORM CONSTRAINT: {platform_directive} "
            "\n\nOutput ONLY the enhanced prompt text. No markdown. Target 300 words."
        )
    elif scale == "asset":
        enhance_system = (
            "You are 'Overlord Creative Director.' Transform user ideas into a VIVID, "
            "DESCRIPTIVE specification for a SINGLE MEDIA ASSET (Image or Video). "
            "Describe the subject, style, lighting, composition, and technical details. "
            "Do NOT mention code, UI, or applications. Focus ONLY on the creative output. "
            "\n\nOutput ONLY the enhanced content description. No markdown. Target 200 words."
        )

    try:
        enhanced = ask_llm(client, model, enhance_system, raw_prompt)
        log("SYSTEM", "  ✓ Prompt enhanced successfully")
        preview_lines = enhanced.strip().split("\n")[:3]
        for line in preview_lines:
            if line.strip():
                log("SYSTEM", f"    → {line.strip()[:100]}")
        return enhanced
    except Exception as e:
        log("WARN", f"  Prompt enhancement failed: {e}. Using original prompt.")
        return raw_prompt


# ── Blueprint Generator (Phase 1) ───────────────────────────

def generate_blueprint(client, model: str, prompt: str, profile: dict,
                       platform_directive: str, media_status: str = "",
                       version_advisory: str = "", research_report: str = "",
                       scale: str = "app") -> dict:
    """Call the Architect LLM to produce a Package Manifest JSON."""

    arch_system = (
        "You are 'Overlord,' an autonomous Senior Full-Stack Engineer and DevOps Specialist. "
        "Directive: No Hallucinations. Do not use placeholder domains or URLs like 'example.com'. "
        "Use real public APIs or write self-contained logic with functional mocks if needed. "
        "Mission: Zero-Interaction Planning. Decompose user intent into a logical file structure. "
        "MEDIA ENGINE: You have access to a unified media engine with image generation "
        "(Flux 2.0, Adobe Firefly, Midjourney, Ideogram) via 'from media_engine import MediaEngine'. "
        f"{media_status}. "
        f"\n\nPLATFORM CONSTRAINT: {platform_directive} "
        "\n\nTECH STACK CONSTRAINT (Stable-Gold Stack):"
        "\nYou MUST prioritize these libraries for ALL projects unless technically impossible:"
        "\n1. FRONTEND: TypeScript is mandatory. Use Tailwind CSS for styling."
        "\n2. BACKEND: Use FastAPI for Python-based logic; avoid Flask for high-concurrency tasks."
        "\n3. DATABASE: Default to PostgreSQL. Include a 'schema.prisma' file if using Prisma."
        "\n4. DOCUMENTATION: Every project must include a detailed 'README.md' and '.env.example'."
    )

    if scale == "app":
        arch_system += (
            "\n\nARCHITECTURE DEPTH STANDARDS (MANDATORY):"
            "\n- Plan AT LEAST 8-15 files for any non-trivial project. Think in MODULES, not monoliths."
            "\n- Separate concerns: components/, utils/, lib/, config/, seed/ folders as appropriate."
            "\n- ALWAYS include a seed/demo data file so the app has realistic data on first run."
            "\n- ALWAYS include a config or constants module for environment variables and settings."
            "\n- ALWAYS include utility/helper modules. Do NOT cram everything into main.py."
            "\n- For web apps: plan separate files for each page/view, each API route group, "
            "  each data model, and shared components (navbar, sidebar, cards, tables, charts)."
            "\n- Include analytics/dashboard views with chart components wherever data is displayed."
            "\n- Plan for search, filter, sort, and pagination in any data-heavy view."
        )

    arch_system += (
        f"{version_advisory}"
        f"\n\n{research_report if research_report else ''}"
        "\n\nOutput ONLY valid JSON with this exact 'Package Manifest' schema: "
        '{"project_name": "<slug_name>", '
        '"stack": {"frontend": "<framework>", "backend": "<framework>", "database": "<provider>"}, '
        '"file_tree": ["path/file.ext", ...], '
        '"files": [{"path": "filename.ext", "task": "description"}], '
        '"dependencies": ["package1"], '
        '"run_command": "' + profile["run_command"] + '", '
        '"mermaid": "graph TD; ... (a complete Mermaid.js flowchart of the system architecture)"}} '
        "Every project MUST include a main entry point and a README.md. "
        f"{PRODUCTION_SAFETY_DIRECTIVE}"
        "\nOutput ONLY raw JSON. No markdown."
    )

    if scale == "script":
        arch_system = (
            "You are 'Overlord Script Engineer.' Create a blueprint for a clean, modular "
            "STANDALONE SCRIPT. Limit the file tree to 1-3 files maximum (main.py, utils.py). "
            "Ignore all UI, monitoring, and dashboard requirements. "
            "\n\nOutput ONLY valid JSON manifest."
        )
    elif scale == "asset":
        arch_system = (
            "You are 'Overlord Asset Generator.' Create a blueprint for a SINGLE ASSET. "
            "The file tree should contain EXACTLY ONE file: 'asset_metadata.json' or 'render_manifest.json'. "
            "This manifest will be used by the MediaEngine to produce the final file. "
            "\n\nOutput ONLY valid JSON manifest."
        )

    try:
        raw_plan = ask_llm(client, model, arch_system, prompt)
        plan = json.loads(raw_plan)
    except json.JSONDecodeError:
        log("ERROR", "Architect returned invalid JSON. Retrying…")
        try:
            raw_plan = ask_llm(client, model, arch_system + " Output raw JSON only.", prompt)
            plan = json.loads(raw_plan)
        except Exception as e:
            log("ERROR", f"Architect failed on retry: {e}")
            raise
    except Exception as e:
        log("ERROR", f"Architect failed: {e}")
        raise

    files = plan.get("files", [])
    deps = plan.get("dependencies", [])
    run_cmd = plan.get("run_command", profile["run_command"])
    stack = plan.get("stack", {})

    log("ARCHITECT", f"Blueprint ready — {len(files)} file(s), {len(deps)} dep(s)")
    if stack:
        log("ARCHITECT", f"  Stack: {json.dumps(stack)}")
    for f in files:
        log("ARCHITECT", f"  ├─ {f['path']}  →  {f['task'][:60]}")
    log("ARCHITECT", f"  └─ run: {run_cmd}")

    # Save Mermaid diagram if present
    mermaid = plan.get("mermaid")
    if mermaid:
        try:
            # We don't have the project_path here, so we return it to the orchestrator to save
            log("ARCHITECT", "  🎨 Visual Blueprint generated (Mermaid.js)")
        except Exception as e:
            log("WARN", f"  Failed to prepare Mermaid diagram: {e}")

    return plan


# ── Platform Resolution ─────────────────────────────────────

def resolve_platform(prompt: str, platform: str = "python") -> tuple:
    """Return (profile dict, platform_directive string)."""
    studio_mode = any(word in prompt.lower() for word in STUDIO_KEYWORDS)
    if studio_mode and platform == "python":
        log("ARCHITECT", "  ✨ STUDIO MODE DETECTED — Activating High-Performance Profile")
        profile = PLATFORM_PROFILES["studio"]
    else:
        profile = PLATFORM_PROFILES.get(platform, PLATFORM_PROFILES["python"])
    return profile, profile["arch_directive"]
