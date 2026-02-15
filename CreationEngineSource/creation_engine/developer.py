"""
Creation Engine — Developer Agent
Handles Phase 2: writes code file-by-file using the Architect's blueprint,
leveraging RAG context, manifest state, import contracts, and wisdom rules.
"""

import os

from .config import (
    PRODUCTION_SAFETY_DIRECTIVE,
    STABILITY_DIRECTIVE,
    FEATURE_RICHNESS_DIRECTIVE,
    API_CONVENTIONS,
)
from .llm_client import log, ask_llm
from .validators import (
    build_manifest,
    manifest_to_context,
    ReviewerAgent,
    SelfCorrectionModule,
)
from .wisdom import WisdomGuard


def write_file(client, model: str, file_spec: dict, file_index: int,
               total_files: int, file_list: list, written_files: dict,
               deps: list, proj_state, rag, wisdom, wisdom_guard: WisdomGuard,
               reviewer: ReviewerAgent, state, eng_model: str = None) -> str:
    """Write a single file: LLM generation → review → wisdom → lint → save.
    Returns the final code string."""

    fpath = file_spec["path"]
    ftask = file_spec["task"]
    eng_model = eng_model or model

    log("ENGINEER", f"[{file_index}/{total_files}] Writing: {fpath}")

    # ── Pillar 1: RAG-Powered Context + Global State ──
    manifest = build_manifest(written_files, planned_files=file_list)
    manifest_ctx = manifest_to_context(manifest) if manifest else "No files written yet."
    symbol_table = proj_state.get_symbol_table()
    rag_context = rag.get_relevant_context(fpath, ftask, symbol_table)

    # Extract import contract from main.py if available
    import_contract = ""
    if "main.py" in written_files and fpath != "main.py":
        main_code = written_files["main.py"]
        module_base = fpath.replace(".py", "")
        relevant_imports = [
            line.strip() for line in main_code.split("\n")
            if module_base in line.strip() and "import" in line.strip()
        ]
        if relevant_imports:
            import_contract = (
                f"\n\nCRITICAL CONTRACT — main.py imports from YOUR file:\n"
                + "\n".join(f"  {imp}" for imp in relevant_imports)
                + "\nYou MUST export these exact function/class names. Do NOT rename them."
            )

    # Build dependency-aware API conventions
    api_conv_parts = []
    for dep_name in deps:
        dep_lower = dep_name.lower().split("==")[0].split(">=")[0].strip()
        if dep_lower in API_CONVENTIONS:
            api_conv_parts.append(API_CONVENTIONS[dep_lower])
        if dep_lower in ("pillow", "pil"):
            api_conv_parts.append(API_CONVENTIONS.get("pillow", ""))
    api_conv_block = ""
    if api_conv_parts:
        api_conv_block = (
            "\n\nLIBRARY API CONVENTIONS (use these EXACT patterns):\n"
            + "\n".join(f"- {c}" for c in api_conv_parts if c)
        )

    wisdom_rules = wisdom.get_generation_rules()

    eng_system = (
        "You are 'Overlord,' an autonomous Senior Full-Stack Engineer. "
        "Directive: Modular Engineering. Write clean, documented code using proper imports. "
        "IMPORTANT: NEVER use placeholder URLs, dummy credentials, or broken 'example.com' domains. "
        "Use functional logic. If an API is unknown, use a robust mock or public test endpoint. "
        "Directive: Self-healing. Anticipate failures with clean try-except blocks. "
        "Directive: Loop Safety. EVERY 'while' loop MUST contain 'time.sleep()' or 'await asyncio.sleep()' to prevent CPU hangs. "
        "Directive: Platform Safety. Avoid 'curses' on Windows; use 'rich' or 'colorama' for CLI UIs. "
        "Directive: Feature-Rich. Build IMPRESSIVE implementations, not bare-minimum stubs. "
        "Every file you write should demonstrate senior-level engineering with thorough edge-case handling. "
        f"Structure: {file_list}. Target: {fpath}. Task: {ftask}. "
        f"{import_contract}"
        f"\n\n{symbol_table}"
        f"{wisdom.get_generation_rules_directive()}"
        f"{PRODUCTION_SAFETY_DIRECTIVE}"
        f"{STABILITY_DIRECTIVE}"
        f"{FEATURE_RICHNESS_DIRECTIVE}"
        f"{api_conv_block}"
        "\nOutput ONLY raw source code. No markdown fences, no explanations."
    )

    if wisdom_rules:
        eng_system += f"\n\n{wisdom_rules}"

    user_prompt = (
        f"Construct the file: {fpath}\n\n"
        f"Relevant context (RAG-selected):\n{rag_context}\n\n"
        f"Full manifest:\n{manifest_ctx}"
    )

    try:
        code = ask_llm(client, eng_model, eng_system, user_prompt)
    except Exception as e:
        log("ERROR", f"Engineer failed on {fpath}: {e}")
        return ""

    # ── REVIEWER GATE (Zero-Inference Loop) ──
    review_count = 0
    for review_attempt in range(3):
        verdict = reviewer.review(fpath, code, manifest_ctx)
        review_count = review_attempt + 1
        if verdict["status"] == "APPROVED":
            log("REVIEWER", f"  ✓ APPROVED: {fpath} (pass {review_count})")
            break
        else:
            log("REVIEWER", f"  ✗ REJECTED [{review_count}/3]: {verdict['reason'][:100]}")
            if review_attempt < 2:
                try:
                    code = ask_llm(client, eng_model, eng_system,
                        f"{user_prompt}\n\nYour previous code was REJECTED.\n"
                        f"Reason: {verdict['reason']}\n"
                        f"Fix ALL issues and output the complete corrected code.")
                except Exception as e:
                    log("REVIEWER", f"  ⚠ Rewrite failed: {e} — accepting current version.")
                    break

    # ── Wisdom Review Gate ──
    wisdom_violations = wisdom.review_against_wisdom(code, fpath)
    if wisdom_violations:
        log("WISDOM", f"  ⚠ {len(wisdom_violations)} wisdom violation(s) in {fpath}")
        wisdom_report = "\n".join(
            f"- VIOLATION: {wv['rule']}\n  FIX: {wv['fix']}" for wv in wisdom_violations
        )
        try:
            code = ask_llm(client, eng_model, eng_system,
                f"WISDOM REVIEW FAILED for {fpath}.\n"
                f"The following known rules were violated:\n{wisdom_report}\n\n"
                f"Fix ALL violations. Output ONLY the corrected complete source code:\n\n{code}")
            log("WISDOM", f"  ✓ Self-corrected {fpath} against wisdom rules")
        except Exception as e:
            log("WISDOM", f"  ⚠ Wisdom correction failed: {e}")

    # ── Self-Correction Module (lint + auto-repair) ──
    def _fixer_callback(broken_code, error_report):
        return ask_llm(client, eng_model, eng_system,
            f"Your previous code has errors:\n{error_report}\n\n"
            f"Fix ALL issues. Output ONLY the corrected complete source code:\n\n{broken_code}")

    corrector = SelfCorrectionModule(code, fpath, max_attempts=3)
    code = corrector.repair_loop(_fixer_callback)

    # ── Wisdom Guard: Deterministic pre-save validation ──
    code, wisdom_fixes = wisdom_guard.auto_fix(code, fpath)
    if wisdom_fixes:
        log("WISDOM", f"  🛡️ Auto-fixed {len(wisdom_fixes)} violation(s) in {fpath}")
        for wf in wisdom_fixes:
            log("WISDOM", f"    → {wf}")

    # ── Save to disk and update state ──
    return code


def write_all_files(client, model: str, plan: dict, project_path: str,
                    written_files: dict, state, proj_state, rag,
                    wisdom, reviewer: ReviewerAgent,
                    eng_model: str = None) -> dict:
    """Write all files from the Architect's plan. Returns updated written_files dict."""

    files = plan.get("files", [])
    deps = plan.get("dependencies", [])
    file_list = [f["path"] for f in files]
    wisdom_guard = WisdomGuard()

    # Strategy: Write main.py FIRST
    main_entry = None
    other_files = []
    for f in files:
        if f["path"] == "main.py":
            main_entry = f
        else:
            other_files.append(f)

    ordered_files = ([main_entry] + other_files) if main_entry else list(files)

    for i, file_spec in enumerate(ordered_files, 1):
        fpath = file_spec["path"]
        code = write_file(
            client=client,
            model=model,
            file_spec=file_spec,
            file_index=i,
            total_files=len(ordered_files),
            file_list=file_list,
            written_files=written_files,
            deps=deps,
            proj_state=proj_state,
            rag=rag,
            wisdom=wisdom,
            wisdom_guard=wisdom_guard,
            reviewer=reviewer,
            state=state,
            eng_model=eng_model,
        )

        if code:
            # Write to disk
            full_path = os.path.join(project_path, fpath)
            os.makedirs(os.path.dirname(full_path) or project_path, exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(code)

            # Update state
            state.write(fpath, code)
            written_files[fpath] = code
            proj_state.register_file(fpath, code)
            rag.index_file(fpath, code, proj_state.get_exports_for(fpath))

    return written_files
