"""
Creation Engine — Modular AI Code Generation Framework

The Creation Engine is a multi-agent framework that architects, develops,
and self-corrects programs in a recursive loop until the child program
runs without errors.

Agents:
    Orchestrator  — manages state machine and agent hand-offs
    Architect     — drafts file structure and logic
    Developer     — writes actual implementation per file
    Supervisor    — runs code in sandbox and captures errors

Usage:
    from creation_engine import CreationEngine

    engine = CreationEngine(
        project_name="my-app",
        prompt="A personal finance app with CSV upload",
        output_dir="./output",
        model="gemini-2.0-flash",
    )
    result = engine.run()
"""

from .orchestrator import CreationEngine, MultiAgentOrchestrator
from .deployment_manager import DeploymentManager
from .visual_verifier import VisualVerifier
from .packaging import OneHandoffPackager
from .llm_client import log, divider, ask_llm, CostTracker, KeyPool
from .config import (
    PRODUCTION_SAFETY_DIRECTIVE,
    STABILITY_DIRECTIVE,
    FEATURE_RICHNESS_DIRECTIVE,
    PLATFORM_PROFILES,
    PROVIDERS,
    PKG_MAP,
    API_CONVENTIONS,
)
from .wisdom import GlobalWisdom, WisdomGuard, AuraRegistry
from .validators import (
    CodebaseState, ProjectState, CodebaseRAG,
    ReviewerAgent, build_manifest, validation_gate,
    DependencyVerifier, SelfCorrectionModule,
    project_assembler,
)
from .architect import enhance_prompt, generate_blueprint, resolve_platform
from .developer import write_file, write_all_files
from .supervisor import Supervisor, SupervisorResult
from .decompiler import NexusDecompiler

__version__ = "1.0.0"
__all__ = [
    "CreationEngine",
    "log", "divider", "ask_llm", "CostTracker", "KeyPool",
    "GlobalWisdom", "WisdomGuard", "AuraRegistry",
    "CodebaseState", "ProjectState", "CodebaseRAG",
    "ReviewerAgent", "build_manifest", "validation_gate",
    "DependencyVerifier", "SelfCorrectionModule",
    "project_assembler",
    "enhance_prompt", "generate_blueprint", "resolve_platform",
    "write_file", "write_all_files",
    "Supervisor", "SupervisorResult",
    "PRODUCTION_SAFETY_DIRECTIVE", "STABILITY_DIRECTIVE",
    "FEATURE_RICHNESS_DIRECTIVE", "PLATFORM_PROFILES",
    "PROVIDERS", "PKG_MAP", "API_CONVENTIONS",
]
