#!/usr/bin/env python3
"""
===============================================================
  TEST: Pipeline Upgrades Verification
  Validates all 3 new features — NO API keys needed.
  
  1. ConstraintMemory (persistent learning)
  2. Performance Reviewer node (exists and returns valid state)
  3. Code Signer (HMAC-SHA256 signing + verification)
  4. Graph topology (new nodes registered)
===============================================================
"""

import os
import sys
import json
import tempfile
import shutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)


# ===============================================================
#  TEST 1: ConstraintMemory
# ===============================================================

def test_constraint_memory_load_save():
    """ConstraintMemory loads existing rules and saves new ones."""
    from overlord_graph import ConstraintMemory

    with tempfile.TemporaryDirectory() as td:
        # Seed a constraints file
        seed = {
            "project_heritage": ["TestProject"],
            "permanent_rules": [
                {"id": "TST-001", "issue": "Test Issue", "lesson": "Test lesson"}
            ],
            "prohibited_patterns": ["eval() in production"],
        }
        path = os.path.join(td, "permanent_constraints.json")
        with open(path, "w") as f:
            json.dump(seed, f)

        cm = ConstraintMemory(memory_dir=td)
        assert cm.rule_count == 1, f"Expected 1 rule, got {cm.rule_count}"
        assert "TST-001" in cm.get_rules_directive()
        assert "eval() in production" in cm.get_rules_directive()
        print("  [PASS] ConstraintMemory: loads existing rules correctly")


def test_constraint_memory_learn_from_rejection():
    """ConstraintMemory auto-learns from Guardian rejection reports."""
    from overlord_graph import ConstraintMemory

    with tempfile.TemporaryDirectory() as td:
        cm = ConstraintMemory(memory_dir=td)
        assert cm.rule_count == 0

        # Simulate a rejection
        fake_report = {
            "status": "REJECTED",
            "issues": [
                {
                    "file": "app.py",
                    "severity": "HIGH",
                    "description": "Hardcoded API key in config",
                    "fix": "Use environment variable instead",
                },
                {
                    "file": "server.py",
                    "severity": "LOW",
                    "description": "Minor style issue",
                    "fix": "Cosmetic fix",
                },
            ],
        }
        cm.learn_from_rejection(fake_report)

        # Should have learned 1 rule (HIGH severity only, LOW is skipped)
        assert cm.rule_count == 1, f"Expected 1 rule, got {cm.rule_count}"
        
        # Verify persisted to disk
        with open(cm.path, "r") as f:
            saved = json.load(f)
        assert len(saved["permanent_rules"]) == 1
        assert "Hardcoded API key" in saved["permanent_rules"][0]["issue"]
        print("  [PASS] ConstraintMemory: learns from rejection (HIGH only)")


def test_constraint_memory_dedup():
    """ConstraintMemory deduplicates learned rules."""
    from overlord_graph import ConstraintMemory

    with tempfile.TemporaryDirectory() as td:
        cm = ConstraintMemory(memory_dir=td)

        report = {
            "issues": [
                {"severity": "HIGH", "description": "SQL Injection", "fix": "Use parameterized queries"}
            ]
        }
        cm.learn_from_rejection(report)
        cm.learn_from_rejection(report)  # Same issue again

        assert cm.rule_count == 1, f"Expected 1 rule after dedup, got {cm.rule_count}"
        print("  [PASS] ConstraintMemory: deduplicates repeated failures")


# ===============================================================
#  TEST 2: Performance Reviewer Node
# ===============================================================

def test_performance_reviewer_exists():
    """performance_reviewer_node is importable and callable."""
    from overlord_graph import performance_reviewer_node
    assert callable(performance_reviewer_node)
    print("  [PASS] performance_reviewer_node: exists and is callable")


def test_performance_reviewer_empty_files():
    """Performance reviewer handles empty written_files gracefully."""
    from overlord_graph import performance_reviewer_node

    state = {
        "client": None,
        "eng_model": "test",
        "review_model": "test",
        "written_files": {},
    }
    result = performance_reviewer_node(state)
    assert result["perf_report"]["status"] == "OPTIMIZED"
    assert result["perf_report"]["suggestions"] == []
    print("  [PASS] performance_reviewer_node: handles empty files gracefully")


# ===============================================================
#  TEST 3: Code Signer
# ===============================================================

def test_code_signer_sign_and_verify():
    """Sign a temp project and verify the signature."""
    from code_signer import sign_build, verify_build

    with tempfile.TemporaryDirectory() as td:
        # Create a fake project
        with open(os.path.join(td, "main.py"), "w") as f:
            f.write("print('hello world')\n")
        with open(os.path.join(td, "utils.py"), "w") as f:
            f.write("def helper(): pass\n")
        with open(os.path.join(td, "README.md"), "w") as f:
            f.write("# Test Project\n")

        key_path = os.path.join(td, ".signing_key")
        report = sign_build(td, signer_id="TestSigner", key_path=key_path)

        assert report["files_signed"] == 3, f"Expected 3 signed files, got {report['files_signed']}"
        assert report["algorithm"] == "HMAC-SHA256"
        assert report["signer"] == "TestSigner"
        assert len(report["signature"]) == 64  # SHA-256 hex = 64 chars
        assert os.path.exists(os.path.join(td, "BUILD_SIGNATURE.json"))

        # Verify untampered
        result = verify_build(td, key_path=key_path)
        assert result["valid"] is True, f"Expected valid=True, got {result}"
        assert result["tampered_files"] == [], f"Got tampered files: {result['tampered_files']}"
        print("  [PASS] code_signer: sign + verify roundtrip")


def test_code_signer_tamper_detection():
    """Tampering with a file invalidates the signature."""
    from code_signer import sign_build, verify_build

    with tempfile.TemporaryDirectory() as td:
        main_path = os.path.join(td, "main.py")
        with open(main_path, "w") as f:
            f.write("print('hello')\n")

        key_path = os.path.join(td, ".signing_key")
        sign_build(td, key_path=key_path)

        # Tamper!
        with open(main_path, "w") as f:
            f.write("import os; os.system('malicious')\n")

        result = verify_build(td, key_path=key_path)
        assert result["valid"] is False
        assert "main.py" in result["tampered_files"]
        print("  [PASS] code_signer.verify_build: detects tampered file")


def test_code_signer_skips_binaries():
    """Signer only signs source files, ignores binaries."""
    from code_signer import hash_project

    with tempfile.TemporaryDirectory() as td:
        with open(os.path.join(td, "main.py"), "w") as f:
            f.write("pass\n")
        with open(os.path.join(td, "image.png"), "wb") as f:
            f.write(b"\x89PNG\r\n")
        with open(os.path.join(td, "app.exe"), "wb") as f:
            f.write(b"\x00\x00")

        hashes = hash_project(td)
        assert "main.py" in hashes
        assert "image.png" not in hashes
        assert "app.exe" not in hashes
        print("  [PASS] code_signer.hash_project: signs source, ignores binaries")


# ===============================================================
#  TEST 4: Graph Topology
# ===============================================================

def test_graph_has_new_nodes():
    """build_factory includes performance_reviewer and signing nodes."""
    try:
        from overlord_graph import build_factory
        graph = build_factory()
        
        # LangGraph compiled graphs expose node names
        node_names = set(graph.nodes.keys()) if hasattr(graph, 'nodes') else set()
        
        assert "performance_reviewer" in node_names, f"Missing performance_reviewer. Nodes: {node_names}"
        assert "signing" in node_names, f"Missing signing. Nodes: {node_names}"
        assert "guardian" in node_names, f"Missing guardian. Nodes: {node_names}"
        print("  [PASS] build_factory: graph includes performance_reviewer + signing nodes")
    except ImportError as e:
        print(f"  [SKIP] build_factory: skipped (langgraph not installed: {e})")


def test_signing_node_exists():
    """signing_node is importable and callable."""
    from overlord_graph import signing_node
    assert callable(signing_node)
    print("  [PASS] signing_node: exists and is callable")


# ===============================================================
#  TEST 5: ConstraintMemory loads real file
# ===============================================================

def test_constraint_memory_loads_real_file():
    """ConstraintMemory successfully loads the real permanent_constraints.json."""
    from overlord_graph import ConstraintMemory

    real_memory_dir = os.path.join(SCRIPT_DIR, "memory")
    if not os.path.exists(os.path.join(real_memory_dir, "permanent_constraints.json")):
        print("  [SKIP] Real constraints file not found, skipping")
        return

    cm = ConstraintMemory(memory_dir=real_memory_dir)
    assert cm.rule_count >= 4, f"Expected >=4 rules, got {cm.rule_count}"
    directive = cm.get_rules_directive()
    assert "PERMANENT CONSTRAINTS" in directive
    assert "RES-001" in directive  # The API rate-limiting rule
    print(f"  [PASS] ConstraintMemory: loaded {cm.rule_count} real rule(s)")


# ===============================================================
#  RUNNER
# ===============================================================

if __name__ == "__main__":
    print("\n=== Pipeline Upgrades — Verification Tests ===\n")
    passed = 0
    failed = 0

    tests = [
        # Constraint Memory
        test_constraint_memory_load_save,
        test_constraint_memory_learn_from_rejection,
        test_constraint_memory_dedup,
        test_constraint_memory_loads_real_file,
        # Performance Reviewer
        test_performance_reviewer_exists,
        test_performance_reviewer_empty_files,
        # Code Signer
        test_code_signer_sign_and_verify,
        test_code_signer_tamper_detection,
        test_code_signer_skips_binaries,
        # Graph Topology
        test_graph_has_new_nodes,
        test_signing_node_exists,
    ]

    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {test_fn.__name__}: {e}")
            failed += 1

    print(f"\n{'=' * 45}")
    print(f"  Results: {passed} passed, {failed} failed")
    print(f"{'=' * 45}\n")
    sys.exit(0 if failed == 0 else 1)
