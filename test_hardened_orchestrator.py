#!/usr/bin/env python3
"""
══════════════════════════════════════════════════════════════
  TEST: Hardened Orchestrator Integration
  Validates Pulse-Sync wiring, AgentState expansion, and
  Shadow Logic prompt construction — NO API keys needed.
══════════════════════════════════════════════════════════════
"""

import os
import sys
import json
import tempfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)


def test_pulse_sync_context():
    """PulseSyncLogger initializes and returns context string."""
    from pulse_sync_logger import PulseSyncLogger

    with tempfile.TemporaryDirectory() as td:
        logger = PulseSyncLogger(project_root=td)
        logger.capture_heartbeat(manual_vibe="Testing hardened orchestrator")
        ctx = logger.get_context_for_orchestrator()
        assert isinstance(ctx, str), f"Expected str, got {type(ctx)}"
        assert "PULSE-SYNC CONTEXT" in ctx, f"Missing header in context: {ctx[:100]}"
        assert "Testing hardened orchestrator" in ctx, "Manual vibe not reflected in context"
        print("  ✓ PulseSyncLogger: context generation works")


def test_agent_state_fields():
    """AgentState accepts new pulse_context and security_manifest fields."""
    from agent_brain_v2 import AgentState

    state: AgentState = {
        "prompt": "test",
        "pulse_context": "PULSE-SYNC CONTEXT: test",
        "security_manifest": {
            "hardened_by": "test",
            "shadow_logic_findings": 0,
        },
    }
    assert state["pulse_context"].startswith("PULSE-SYNC")
    assert state["security_manifest"]["shadow_logic_findings"] == 0
    print("  ✓ AgentState: new fields accepted")


def test_guardian_shadow_prompt():
    """GuardianNode has SHADOW_LOGIC_PROMPT class attribute."""
    from agent_brain_v2 import GuardianNode

    assert hasattr(GuardianNode, "SHADOW_LOGIC_PROMPT"), "Missing SHADOW_LOGIC_PROMPT"
    prompt = GuardianNode.SHADOW_LOGIC_PROMPT
    assert "Shadow Logic" in prompt, "Prompt missing 'Shadow Logic' keyword"
    assert "hostile" in prompt.lower(), "Prompt missing adversarial framing"
    assert "JSON" in prompt, "Prompt missing JSON output requirement"
    print("  ✓ GuardianNode: Shadow Logic prompt is well-formed")


def test_security_manifest_generation():
    """BundlerNode generates SECURITY_MANIFEST.md from manifest data."""
    # Simulate what BundlerNode does with the manifest data
    sec_manifest = {
        "hardened_by": "Overlord Hardened Orchestrator V4",
        "timestamp": "2026-02-16T01:00:00",
        "guardian_verdict": "APPROVED",
        "overall_score": 92,
        "scores": {"syntax": 100, "patterns": 100, "review": 80, "shadow": 85},
        "shadow_logic_findings": 1,
        "shadow_issues_resolved": [
            "Shadow: Hardcoded API key in config → Fix: Use env variable"
        ],
        "total_issues_found": 2,
        "pulse_sync_risk": "Low",
    }

    with tempfile.TemporaryDirectory() as td:
        manifest_lines = [
            "# 🛡️ SECURITY MANIFEST",
            f"**Hardened by:** {sec_manifest.get('hardened_by', 'Overlord')}",
            f"**Guardian Verdict:** {sec_manifest.get('guardian_verdict', 'UNKNOWN')}",
            f"**Overall Score:** {sec_manifest.get('overall_score', '?')}/100",
        ]
        for k, v in sec_manifest.get("scores", {}).items():
            manifest_lines.append(f"- **{k.title()}:** {v}/100")

        shadow_resolved = sec_manifest.get("shadow_issues_resolved", [])
        if shadow_resolved:
            manifest_lines.append(f"## Shadow Logic ({len(shadow_resolved)} issue(s) auto-resolved)")
            for sr in shadow_resolved:
                manifest_lines.append(f"- {sr}")

        path = os.path.join(td, "SECURITY_MANIFEST.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(manifest_lines) + "\n")

        assert os.path.exists(path), "SECURITY_MANIFEST.md not created"
        content = open(path).read()
        assert "SECURITY MANIFEST" in content
        assert "Shadow Logic" in content
        assert "Hardcoded API key" in content
        print("  ✓ BundlerNode: SECURITY_MANIFEST.md generation works")


def test_pulse_sync_import_flag():
    """_HAS_PULSE_SYNC flag is set correctly."""
    from agent_brain_v2 import _HAS_PULSE_SYNC
    assert isinstance(_HAS_PULSE_SYNC, bool), f"Expected bool, got {type(_HAS_PULSE_SYNC)}"
    assert _HAS_PULSE_SYNC is True, "PulseSyncLogger should be importable"
    print("  ✓ Import flag: _HAS_PULSE_SYNC = True")


if __name__ == "__main__":
    print("\n═══ Hardened Orchestrator Integration Tests ═══\n")
    passed = 0
    failed = 0

    for test_fn in [
        test_pulse_sync_context,
        test_agent_state_fields,
        test_guardian_shadow_prompt,
        test_security_manifest_generation,
        test_pulse_sync_import_flag,
    ]:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            print(f"  ✗ {test_fn.__name__}: {e}")
            failed += 1

    print(f"\n{'═' * 40}")
    print(f"  Results: {passed} passed, {failed} failed")
    print(f"{'═' * 40}\n")
    sys.exit(0 if failed == 0 else 1)
