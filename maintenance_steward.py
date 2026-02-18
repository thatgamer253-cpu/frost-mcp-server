#!/usr/bin/env python3
"""
=================================================================
  OVERLORD — Maintenance Steward
  Autonomous dependency health checker for your project library.
  
  Usage:
    python maintenance_steward.py                           # scan ./output
    python maintenance_steward.py --library ./my-projects   # custom path
    python maintenance_steward.py --auto-update              # apply SAFE patches
    python maintenance_steward.py --model llama3             # use local model
=================================================================
"""

import os
import sys
import json
import re
import time
import argparse
from datetime import datetime
from typing import Optional

# ── HTTP client (stdlib only — no requests dependency) ─────────
import urllib.request
import urllib.error

# ── Import Overlord LLM tools if available ─────────────────────
_HAS_BRAIN = False
try:
    from agent_brain import ask_llm, get_cached_client, log, _client_cache
    _HAS_BRAIN = True
except ImportError:
    def log(tag, msg):
        print(f"[{tag}] {msg}")


# ═══════════════════════════════════════════════════════════════
#  SEMVER UTILITIES
# ═══════════════════════════════════════════════════════════════

_VER_RE = re.compile(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?")


def parse_version(ver_str: str) -> tuple:
    """Extract (major, minor, patch) from a version string."""
    m = _VER_RE.search(ver_str)
    if not m:
        return (0, 0, 0)
    return (
        int(m.group(1)),
        int(m.group(2) or 0),
        int(m.group(3) or 0),
    )


def classify_update(current: tuple, latest: tuple) -> str:
    """Classify the gap between two version tuples."""
    if latest[0] > current[0]:
        return "MAJOR"
    if latest[1] > current[1]:
        return "MINOR"
    if latest[2] > current[2]:
        return "PATCH"
    return "UP-TO-DATE"


# ═══════════════════════════════════════════════════════════════
#  REGISTRY QUERIES
# ═══════════════════════════════════════════════════════════════

def _fetch_json(url: str, timeout: int = 10) -> Optional[dict]:
    """Fetch JSON from a URL using stdlib only."""
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, Exception):
        return None


def query_pypi(package: str) -> Optional[str]:
    """Get latest stable version of a PyPI package."""
    data = _fetch_json(f"https://pypi.org/pypi/{package}/json")
    if data and "info" in data:
        return data["info"].get("version")
    return None


def query_npm(package: str) -> Optional[str]:
    """Get latest stable version of an npm package."""
    data = _fetch_json(f"https://registry.npmjs.org/{package}/latest")
    if data:
        return data.get("version")
    return None


# ═══════════════════════════════════════════════════════════════
#  DEPENDENCY PARSERS
# ═══════════════════════════════════════════════════════════════

# Regex for requirements.txt lines: package==1.2.3 or package>=1.2.3 etc.
_REQ_LINE = re.compile(r"^([a-zA-Z0-9_.-]+)\s*[=<>!~]+\s*([^\s,;#]+)", re.MULTILINE)
# Fallback: bare package name with no version pin
_REQ_BARE = re.compile(r"^([a-zA-Z0-9_.-]+)\s*$", re.MULTILINE)


def parse_requirements_txt(path: str) -> dict:
    """Parse requirements.txt → {package: pinned_version or '0.0.0'}."""
    deps = {}
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    for match in _REQ_LINE.finditer(content):
        pkg = match.group(1).lower().strip()
        ver = match.group(2).strip()
        if pkg and not pkg.startswith("#"):
            deps[pkg] = ver

    # Also catch unpinned packages
    for match in _REQ_BARE.finditer(content):
        pkg = match.group(1).lower().strip()
        if pkg and not pkg.startswith("#") and pkg not in deps:
            deps[pkg] = "0.0.0"  # unpinned — always outdated

    return deps


def parse_package_json(path: str) -> dict:
    """Parse package.json → {package: version} from dependencies + devDependencies."""
    deps = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, Exception):
        return deps

    for section in ["dependencies", "devDependencies"]:
        section_deps = data.get(section, {})
        if isinstance(section_deps, dict):
            for pkg, ver in section_deps.items():
                # Strip semver ranges: ^1.2.3 → 1.2.3, ~1.2.3 → 1.2.3
                clean_ver = re.sub(r"^[\^~>=<!\s]+", "", str(ver))
                deps[pkg] = clean_ver if clean_ver else "0.0.0"

    return deps


# ═══════════════════════════════════════════════════════════════
#  PROJECT SCANNER
# ═══════════════════════════════════════════════════════════════

def scan_project(project_path: str) -> dict:
    """
    Scan a single project directory.
    Returns: {
        "name": str,
        "path": str,
        "type": "python" | "node" | "unknown",
        "dependencies": {pkg: {"pinned": str, "latest": str, "update": str}},
    }
    """
    name = os.path.basename(project_path)
    result = {
        "name": name,
        "path": project_path,
        "type": "unknown",
        "dependencies": {},
    }

    req_path = os.path.join(project_path, "requirements.txt")
    pkg_path = os.path.join(project_path, "package.json")

    if os.path.isfile(req_path):
        result["type"] = "python"
        pinned = parse_requirements_txt(req_path)
        log("STEWARD", f"  📦 {name}: {len(pinned)} Python dep(s)")

        for pkg, ver in pinned.items():
            latest = query_pypi(pkg)
            if latest:
                update_class = classify_update(parse_version(ver), parse_version(latest))
                result["dependencies"][pkg] = {
                    "pinned": ver,
                    "latest": latest,
                    "update": update_class,
                }
            else:
                result["dependencies"][pkg] = {
                    "pinned": ver,
                    "latest": "?",
                    "update": "UNKNOWN",
                }
            time.sleep(0.1)  # Be polite to registries

    elif os.path.isfile(pkg_path):
        result["type"] = "node"
        pinned = parse_package_json(pkg_path)
        log("STEWARD", f"  📦 {name}: {len(pinned)} Node dep(s)")

        for pkg, ver in pinned.items():
            latest = query_npm(pkg)
            if latest:
                update_class = classify_update(parse_version(ver), parse_version(latest))
                result["dependencies"][pkg] = {
                    "pinned": ver,
                    "latest": latest,
                    "update": update_class,
                }
            else:
                result["dependencies"][pkg] = {
                    "pinned": ver,
                    "latest": "?",
                    "update": "UNKNOWN",
                }
            time.sleep(0.1)

    return result


# ═══════════════════════════════════════════════════════════════
#  REVIEWER INTEGRATION (Maintenance Branch)
# ═══════════════════════════════════════════════════════════════

COMPAT_SYSTEM = (
    "You are 'Overlord Maintenance Reviewer,' an expert at assessing dependency update risks. "
    "You will receive a project's file tree, the dependency being updated, the version change, "
    "and snippets of code that import or use that dependency. "
    "\n\nYour job: determine if upgrading this dependency will BREAK the existing code. "
    "Look for: deprecated API usage, changed function signatures, removed modules, "
    "and breaking behavioral changes in the new version."
    "\n\nOutput ONLY a JSON object: "
    '{"verdict": "SAFE" or "BREAKING" or "CAUTION", "reason": "concise explanation"}'
    "\nSAFE = upgrade won't break anything. "
    "BREAKING = upgrade will definitely break existing code. "
    "CAUTION = upgrade might break something, manual review recommended."
    "\nOutput ONLY the JSON. No markdown fences."
)


def find_usage_snippets(project_path: str, package: str, max_lines: int = 30) -> str:
    """Find code lines that reference a package in the project."""
    snippets = []
    # Normalize: flask → flask, python-dotenv → dotenv
    import_name = package.replace("-", "_").split("[")[0]

    for root, _dirs, files in os.walk(project_path):
        for fname in files:
            if not fname.endswith((".py", ".js", ".ts", ".jsx", ".tsx")):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
                for i, line in enumerate(lines, 1):
                    if import_name in line.lower() or package in line.lower():
                        rel = os.path.relpath(fpath, project_path)
                        snippets.append(f"  {rel}:{i}  {line.rstrip()}")
            except Exception:
                continue

    return "\n".join(snippets[:max_lines]) if snippets else "(no direct usage found)"


def reviewer_compatibility_check(
    client, model: str, project_path: str, pkg: str,
    pinned: str, latest: str, update_class: str,
) -> dict:
    """Ask the Reviewer LLM if upgrading this package would break the project."""
    # Gather context
    file_tree = []
    for root, _dirs, files in os.walk(project_path):
        for fname in files:
            rel = os.path.relpath(os.path.join(root, fname), project_path)
            if not rel.startswith("."):
                file_tree.append(rel)

    usage = find_usage_snippets(project_path, pkg)

    prompt = (
        f"PROJECT: {os.path.basename(project_path)}\n"
        f"FILE TREE: {file_tree[:30]}\n\n"
        f"DEPENDENCY UPDATE:\n"
        f"  Package: {pkg}\n"
        f"  Current: {pinned}\n"
        f"  Latest:  {latest}\n"
        f"  Change:  {update_class}\n\n"
        f"CODE THAT USES THIS PACKAGE:\n{usage}\n"
    )

    try:
        raw = ask_llm(client, model, COMPAT_SYSTEM, prompt)
        result = json.loads(raw)
        if "verdict" in result:
            return result
        return {"verdict": "CAUTION", "reason": "Reviewer returned unexpected format."}
    except json.JSONDecodeError:
        raw_upper = (raw or "").upper()
        if "BREAKING" in raw_upper:
            return {"verdict": "BREAKING", "reason": raw[:200]}
        if "SAFE" in raw_upper:
            return {"verdict": "SAFE", "reason": raw[:200]}
        return {"verdict": "CAUTION", "reason": "Reviewer response unparseable."}
    except Exception as e:
        return {"verdict": "CAUTION", "reason": f"Reviewer error: {e}"}


# ═══════════════════════════════════════════════════════════════
#  REPORT GENERATOR
# ═══════════════════════════════════════════════════════════════

def print_project_report(scan: dict, reviews: dict):
    """Pretty-print the maintenance report for one project."""
    name = scan["name"]
    deps = scan["dependencies"]

    # Categorize
    major = {k: v for k, v in deps.items() if v["update"] == "MAJOR"}
    minor = {k: v for k, v in deps.items() if v["update"] == "MINOR"}
    patch = {k: v for k, v in deps.items() if v["update"] == "PATCH"}
    current = {k: v for k, v in deps.items() if v["update"] == "UP-TO-DATE"}

    total = len(deps)
    outdated = len(major) + len(minor) + len(patch)

    log("STEWARD", f"{'─' * 55}")
    log("STEWARD", f"📋 {name}  ({scan['type']})  —  {total} deps, {outdated} outdated")
    log("STEWARD", f"{'─' * 55}")

    if not outdated:
        log("STEWARD", "  ✅ All dependencies are up to date!")
        return

    # Table header
    log("STEWARD", f"  {'Package':<25} {'Pinned':<12} {'Latest':<12} {'Level':<8} {'Verdict'}")
    log("STEWARD", f"  {'─'*25} {'─'*12} {'─'*12} {'─'*8} {'─'*12}")

    for pkg, info in sorted(deps.items(), key=lambda x: {"MAJOR": 0, "MINOR": 1, "PATCH": 2}.get(x[1]["update"], 3)):
        if info["update"] == "UP-TO-DATE":
            continue
        verdict = reviews.get(pkg, {}).get("verdict", "—")
        icon = {"SAFE": "✅", "BREAKING": "❌", "CAUTION": "⚠️"}.get(verdict, "  ")
        log("STEWARD", f"  {pkg:<25} {info['pinned']:<12} {info['latest']:<12} {info['update']:<8} {icon} {verdict}")

    log("STEWARD", "")


def save_report(project_path: str, scan: dict, reviews: dict):
    """Save a JSON report file in the project folder."""
    report = {
        "project": scan["name"],
        "scanned_at": datetime.now().isoformat(),
        "type": scan["type"],
        "total_dependencies": len(scan["dependencies"]),
        "dependencies": {},
    }
    for pkg, info in scan["dependencies"].items():
        entry = dict(info)
        if pkg in reviews:
            entry["review"] = reviews[pkg]
        report["dependencies"][pkg] = entry

    report_path = os.path.join(project_path, "maintenance_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    log("STEWARD", f"  📄 Report saved: {report_path}")


# ═══════════════════════════════════════════════════════════════
#  AUTO-UPDATER
# ═══════════════════════════════════════════════════════════════

def auto_update_requirements(project_path: str, scan: dict, reviews: dict):
    """Update requirements.txt with SAFE patch/minor updates."""
    req_path = os.path.join(project_path, "requirements.txt")
    if not os.path.isfile(req_path):
        return

    with open(req_path, "r", encoding="utf-8") as f:
        content = f.read()

    updated_count = 0
    for pkg, info in scan["dependencies"].items():
        if info["update"] == "UP-TO-DATE" or info["latest"] == "?":
            continue

        verdict = reviews.get(pkg, {}).get("verdict", "CAUTION")

        # Only auto-update SAFE patches and minors
        if verdict == "SAFE" and info["update"] in ("PATCH", "MINOR"):
            old_pattern = re.compile(
                rf"^({re.escape(pkg)}\s*==\s*){re.escape(info['pinned'])}",
                re.MULTILINE | re.IGNORECASE,
            )
            new_content = old_pattern.sub(rf"\g<1>{info['latest']}", content)
            if new_content != content:
                content = new_content
                updated_count += 1
                log("STEWARD", f"  ⬆️  {pkg}: {info['pinned']} → {info['latest']}")

    if updated_count > 0:
        with open(req_path, "w", encoding="utf-8") as f:
            f.write(content)
        log("STEWARD", f"  ✓ Updated {updated_count} package(s) in requirements.txt")
    else:
        log("STEWARD", "  No safe auto-updates available.")


# ═══════════════════════════════════════════════════════════════
#  MAIN PIPELINE
# ═══════════════════════════════════════════════════════════════

def run_steward(library_path: str, model: str = "gpt-4o",
                api_key: str = "", auto_update: bool = False):
    """Main entry point: scan all projects, check versions, review, report."""

    log("STEWARD", "═" * 55)
    log("STEWARD", "🛡️  OVERLORD MAINTENANCE STEWARD")
    log("STEWARD", f"   Library: {os.path.abspath(library_path)}")
    log("STEWARD", "═" * 55)

    # Discover projects
    if not os.path.isdir(library_path):
        log("ERROR", f"Library path not found: {library_path}")
        return

    projects = [
        os.path.join(library_path, d)
        for d in sorted(os.listdir(library_path))
        if os.path.isdir(os.path.join(library_path, d)) and not d.startswith(".")
    ]

    if not projects:
        log("STEWARD", "  No projects found in library.")
        return

    log("STEWARD", f"  Found {len(projects)} project(s)")
    log("STEWARD", "")

    # Initialize LLM client for reviewer (if available)
    client = None
    if _HAS_BRAIN:
        try:
            global _client_cache
            _client_cache = {}
            resolved_key = api_key or os.environ.get("OPENAI_API_KEY", "")
            client = get_cached_client(model, resolved_key)
            log("STEWARD", f"  🤖 Reviewer model: {model}")
        except Exception as e:
            log("STEWARD", f"  ⚠ LLM unavailable ({e}) — skipping compatibility reviews")
            client = None
    else:
        log("STEWARD", "  ⚠ agent_brain not importable — skipping LLM reviews")

    log("STEWARD", "")

    # Scan and review each project
    all_reports = []

    for project_path in projects:
        name = os.path.basename(project_path)

        # Check if this project has recognizable dependency files
        has_req = os.path.isfile(os.path.join(project_path, "requirements.txt"))
        has_pkg = os.path.isfile(os.path.join(project_path, "package.json"))

        if not has_req and not has_pkg:
            log("STEWARD", f"  ⏭  {name}: no dependency file found — skipping")
            continue

        log("STEWARD", f"🔍 Scanning: {name}")
        scan = scan_project(project_path)

        # Identify packages that need a Reviewer check (MAJOR + MINOR)
        needs_review = {
            pkg: info for pkg, info in scan["dependencies"].items()
            if info["update"] in ("MAJOR", "MINOR") and info["latest"] != "?"
        }

        reviews = {}
        if needs_review and client:
            log("STEWARD", f"  🧠 Triggering Reviewer for {len(needs_review)} significant update(s)…")
            for pkg, info in needs_review.items():
                log("STEWARD", f"    Reviewing: {pkg} {info['pinned']} → {info['latest']} ({info['update']})")
                verdict = reviewer_compatibility_check(
                    client, model, project_path, pkg,
                    info["pinned"], info["latest"], info["update"],
                )
                reviews[pkg] = verdict
                icon = {"SAFE": "✅", "BREAKING": "❌", "CAUTION": "⚠️"}.get(verdict["verdict"], "❓")
                log("STEWARD", f"      {icon} {verdict['verdict']}: {verdict.get('reason', '')[:80]}")
        elif needs_review:
            log("STEWARD", f"  ⚠ {len(needs_review)} update(s) need review but LLM is unavailable")

        # Mark PATCH updates as SAFE by default (no LLM needed)
        for pkg, info in scan["dependencies"].items():
            if info["update"] == "PATCH" and pkg not in reviews:
                reviews[pkg] = {"verdict": "SAFE", "reason": "Patch-level update — low risk."}

        # Print report
        print_project_report(scan, reviews)

        # Save JSON report
        save_report(project_path, scan, reviews)

        # Auto-update if requested
        if auto_update and scan["type"] == "python":
            auto_update_requirements(project_path, scan, reviews)

        all_reports.append({"scan": scan, "reviews": reviews})

    # Summary
    log("STEWARD", "")
    log("STEWARD", "═" * 55)
    total_deps = sum(len(r["scan"]["dependencies"]) for r in all_reports)
    total_outdated = sum(
        1 for r in all_reports
        for info in r["scan"]["dependencies"].values()
        if info["update"] not in ("UP-TO-DATE", "UNKNOWN")
    )
    total_breaking = sum(
        1 for r in all_reports
        for v in r["reviews"].values()
        if v.get("verdict") == "BREAKING"
    )
    log("STEWARD", f"  📊 Summary: {len(all_reports)} project(s), "
                   f"{total_deps} dep(s), {total_outdated} outdated, "
                   f"{total_breaking} breaking")
    log("STEWARD", "═" * 55)


# ═══════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Overlord Maintenance Steward — Dependency Health Checker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python maintenance_steward.py                             # scan ./output
  python maintenance_steward.py --library ./my-projects     # custom path
  python maintenance_steward.py --auto-update               # apply safe patches
  python maintenance_steward.py --model llama3              # use local model
        """,
    )
    parser.add_argument("--library", default="./output",
                        help="Path to the project library directory (default: ./output)")
    parser.add_argument("--model", default="gpt-4o",
                        help="LLM model for compatibility reviews (default: gpt-4o)")
    parser.add_argument("--api-key", default="",
                        help="API key for the LLM provider")
    parser.add_argument("--auto-update", action="store_true",
                        help="Automatically apply SAFE patch/minor updates to requirements.txt")

    args = parser.parse_args()

    run_steward(
        library_path=args.library,
        model=args.model,
        api_key=args.api_key,
        auto_update=args.auto_update,
    )
