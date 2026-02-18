import os
import sys
import json
import time
from typing import Optional, List

from core.agents import Architect, Engineer, Reviewer
from core.media import MultimodalEngine
from core.specialists.sentinel import Sentinel
from core.specialists.alchemist import Alchemist
from core.bypasses.stealth import StealthEngine

class CreationEngine:
    """
    The Universal Creation Engine.
    Orchestrates the entire lifecycle: Decompile -> Plan -> Build -> Refine -> Validate -> Distribute.
    """
    def __init__(self, project_name: str, output_path: str, model: str = "gpt-4o"):
        self.project_name = project_name
        self.output_path = output_path
        self.model = model
        
        # Initialize Workforce
        self.architect = Architect(model)
        self.engineer = Engineer(model)
        self.reviewer = Reviewer(model)
        self.sentinel = Sentinel()
        self.alchemist = Alchemist()
        self.stealth = StealthEngine()
        self.media = MultimodalEngine()

    def run(self, prompt: str):
        """Executes the full creation pipeline."""
        print(f"[ENGINE] Initiating Build for: {self.project_name}")
        print(f"   Mode: Universal Creation Engine (Modular Core)")
        
        # Phase 1: Planning (Architect)
        print("\n=== PHASE 1: SEMANTIC PLANNING (Architect) ===")
        plan = self.architect.plan(prompt)
        if not plan or "file_tree" not in plan:
            print("[ERROR] Architect failed to produce a valid plan.")
            return False

        project_root = os.path.join(self.output_path, self.project_name)
        os.makedirs(project_root, exist_ok=True)
        
        # Create directory structure
        for path in plan.get("file_tree", []):
            full_path = os.path.join(project_root, path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

        # Phase 2: Code Generation (Engineer)
        print("\n=== PHASE 2: ATOMIC CONSTRUCTION (Engineer) ===")
        generated_files = []
        for file_info in plan.get("files", []):
            rel_path = file_info.get("path")
            task_desc = file_info.get("task")
            if not rel_path: continue
            
            full_path = os.path.join(project_root, rel_path)
            # Create context from related files if needed
            context = f"Project: {self.project_name}\nDescription: {prompt}\nStack: {plan.get('stack', {})}"
            
            code = self.engineer.build_file(rel_path, task_desc, context)
            
            # Write raw code first
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(code)
            
            generated_files.append(full_path)

        # Phase 3: Multimodal Handover (Visual DNA)
        print("\n=== PHASE 3: VISUAL DNA SYNTHESIS (Media Engine) ===")
        # We trigger this *after* code to ensure we have context
        # We need to find where assets should go.
        assets_dir = os.path.join(project_root, "assets", "gen")
        self.media.ensure_asset_dirs(project_root)
        visual_desc = plan.get("visual_identity", prompt) # Use architect's visual identity if available
        image_path = self.media.generate_visual_dna(visual_desc, assets_dir)
        
        if image_path:
             self.media.generate_ux_motion(image_path, assets_dir)
        
        # Phase 4: Refinement & Validation (Alchemist & Sentinel)
        print("\n=== PHASE 4: MOLECULAR REFINEMENT (Specialists) ===")
        success_count = 0
        for file_path in generated_files:
            if not file_path.endswith(".py"): 
                success_count += 1
                continue

            # Alchemist: Purge and Optimize
            self.alchemist.refine(file_path)
            
            # Sentinel: Atomic Validation
            if self.sentinel.audit(file_path):
                success_count += 1
            else:
                 print(f"[WARN] Sentinel rejected: {os.path.basename(file_path)}")

        print(f"\n[SUCCESS] Project '{self.project_name}' ready in {project_root}")
        print(f"   Files Generated: {len(generated_files)}")
        print(f"   Verified Stable: {success_count}/{len(generated_files)}")
        
        return True
