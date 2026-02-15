import os
import sys
import json
import time
import logging
import traceback
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("frost-bridge")

# Add Creator to path
# Try specific desktop path found in system check
creator_path = os.getenv("CREATOR_PATH", r"c:\Users\thatg\Desktop\Creator")
if not os.path.exists(creator_path):
    creator_path = os.path.join(os.path.expanduser("~"), "Desktop", "Creator")

if os.path.exists(creator_path):
    if creator_path not in sys.path:
        sys.path.insert(0, creator_path)
else:
    # Use the bundled source if Desktop path is missing (Cloud/Render Mode)
    relative_path = os.path.join(os.getcwd(), "CreationEngineSource")
    if os.path.exists(relative_path):
        if relative_path not in sys.path:
            sys.path.insert(0, relative_path)
        logger.info(f"BRIDGE: Using bundled Creation Engine source at {relative_path}")

try:
    from creation_engine.orchestrator import CreationEngine as AdvancedEngine
    _HAS_ADVANCED = True
except ImportError:
    if os.getenv("AGENT_MODE") != "production":
        print(f"WARNING: Advanced Creation Engine not found at {creator_path}. Falling back to swarm-local engine.")
    _HAS_ADVANCED = False
    from swarm_creation_engine import CreationEngine as SwarmLocalEngine

class CreationEngineBridge:
    """
    Bridges the Frost Swarm to the Advanced Creation Engine.
    Supports 'new', 'upgrade', and 'reverse' modes.
    """
    def __init__(self):
        if _HAS_ADVANCED:
            # We initialize on demand to save resources if not used
            self.advanced_engine = None
        else:
            self.local_engine = SwarmLocalEngine()

    def _update_dashboard_state(self, project_id, phase, summary, mode="new", target="python"):
        """Writes a state.json compatible with dashboard.py."""
        state_file = f"applications/{project_id}/state.json"
        os.makedirs(os.path.dirname(state_file), exist_ok=True)
        
        current_data = {"current_phase": phase, "history": [], "mode": mode, "target": target}
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r') as f:
                    current_data = json.load(f)
            except: pass
            
        if isinstance(current_data, dict):
            current_data["current_phase"] = phase
            current_data["mode"] = mode
            current_data["target"] = target
            current_data["history"].append({
            "timestamp": time.strftime("%H:%M:%S"),
            "phase": phase,
            "summary": summary,
            "artifacts": []
        })
        
        with open(state_file, "w") as f:
            json.dump(current_data, f, indent=2)

    def build_project(self, project_id, goal, description=""):
        """
        Main entry point for building/upgrading/reversing a project.
        """
        # 1. Mode & Target Detection
        mode = "new"
        target = "python" # Default
        source_path = None
        
        # Heuristics for mode detection
        goal_lower = goal.lower()
        desc_lower = description.lower()
        combined = f"{goal_lower} {desc_lower}"
        
        if any(kw in combined for kw in ["upgrade", "modernize", "migrate", "refactor", "update"]):
            mode = "upgrade"
        elif any(kw in combined for kw in ["reverse engineer", "decompile", "analyze codebase", "disassemble"]):
            mode = "reverse"

        # Platform/Target Detection
        if any(kw in combined for kw in ["android", "mobile app", "apk", "kotlin"]):
            target = "android"
        elif any(kw in combined for kw in ["linux", "desktop app", "gtk", "ubuntu", "debian", "fedora"]):
            target = "linux"
        elif any(kw in combined for kw in ["game", "pygame", "unity", "unreal", "studio", "creative", "media app"]):
            target = "studio"
        elif any(kw in combined for kw in ["windows", "exe", "desktop", "win32"]):
            target = "python" # Standard python often builds to Windows EXE via bundler

        # Check for path-like strings in description for upgrade/reverse
        import re
        paths = re.findall(r'[a-zA-Z]:\\[\w\\\-\.]+', description)
        if paths:
            source_path = paths[0]
            print(f"BRIDGE: Detected source path: {source_path}")

        if _HAS_ADVANCED:
            return self._run_advanced_build(project_id, goal, description, mode, source_path, target)
        else:
            return self.local_engine.build_project(project_id, goal, description)

    def _run_advanced_build(self, project_id, goal, description, mode, source_path, target):
        """Wraps the Creator's AdvancedEngine."""
        from revenue import RevenueManager
        rev_manager = RevenueManager()
        
        # 1. Routing: Use 'marketplace/' for commercial/agent builds
        is_commercial = any(kw in f"{goal} {description}".lower() for kw in ["sell", "commercial", "shop", "productize", "for sale"])
        is_intra_hive = any(kw in f"{goal} {description}".lower() for kw in ["to agents", "intra-hive", "agent-to-agent", "for the swarm"])
        is_inter_hive = any(kw in f"{goal} {description}".lower() for kw in ["other people's agents", "external swarms", "inter-hive", "cross-swarm"])
        
        base_dir = "marketplace" if (is_commercial or is_intra_hive or is_inter_hive) else "applications"
        output_dir = os.path.abspath(base_dir)
        
        # 2. Revenue Tracking: Estimate value and record pending income
        if is_commercial or is_inter_hive:
            # Simple heuristic valuation for the 'Cash Machine' dashboard
            est_value = 499.0 if is_inter_hive else 199.0
            rev_manager.record_job_start(project_id, "Marketplace", est_value)
            print(f"BRIDGE: Revenue logic active. Recorded potential value: ${est_value:.2f}")

        # 3. INITIAL STATUS
        self._update_dashboard_state(project_id, "INIT", f"Starting {mode} build for project: {project_id} (Target: {target} | Route: {base_dir})", mode, target)
        
        # Combine goal and description for the prompt
        full_prompt = f"Goal: {goal}\nDescription: {description}\nTarget: {target}"
        
        # 2. Commercial/Sell Mode Logic
        is_commercial = any(kw in f"{goal} {description}".lower() for kw in ["sell", "commercial", "shop", "productize", "for sale"])
        is_intra_hive = any(kw in f"{goal} {description}".lower() for kw in ["to agents", "intra-hive", "agent-to-agent", "for the swarm"])
        is_inter_hive = any(kw in f"{goal} {description}".lower() for kw in ["other people's agents", "external swarms", "inter-hive", "cross-swarm"])
        
        if is_commercial or is_intra_hive or is_inter_hive:
            if is_inter_hive:
                directive = """
                INTER-HIVE DIRECTIVE: This project is for EXTERNAL AGENT CONSUMPTION.
                1. Focus on UNIVERSAL STANDARDS (OpenAPI/Swagger, Standard Markdown).
                2. Include a 'SWARM_README.md' strictly for external AI parsing.
                3. Implement secure, token-based licensing placeholders.
                4. Package as a self-contained, portable module with a 'swarm-init.sh'.
                """
                print(f"BRIDGE: Inter-Hive Marketplace Mode Active. Injecting Cross-Swarm Directives.")
            elif is_intra_hive:
                directive = """
                INTRA-HIVE DIRECTIVE: This project is for AGENT-TO-AGENT TRADING.
                1. Focus on EXTREME MODULARITY (Plugin architecture).
                2. Standardize all data exchanges using JSON APIs.
                3. Include an 'agent_integrate.py' script for automated swarm adoption.
                4. Document strictly for technical consumption by other AI agents.
                """
                print(f"BRIDGE: Intra-Hive Marketplace Mode Active. Injecting Hive Directives.")
            else:
                directive = """
                COMMERCIAL DIRECTIVE: This project is intended for SALE. 
                1. Ensure all source files include standard MIT license headers.
                2. Generate a professional 'README_PRODUCT.md' for the end-user.
                3. If software, include a 'setup.py' or 'requirements.txt' for easy deployment.
                4. Focus on high-visibility 'WOW' factors in UI/UX if applicable.
                """
                print(f"BRIDGE: Commercial Mode Active. Injecting Productization Directives.")
            
            full_prompt += f"\n\n{directive}"
        
        # Initialize the advanced engine
        try:
            # Note: The AdvancedEngine in Desktop/Creator expects 'project_name', 'prompt', etc.
            # We pass the target in the prompt for now as the orchestrator uses profile keywords.
            engine = AdvancedEngine(
                project_name=project_id,
                prompt=full_prompt,
                output_dir=output_dir,
                model="gpt-4o", # Default to robust model
                mode=mode,
                source_path=source_path,
                docker=True
            )
            
            print(f"BRIDGE: Initializing Advanced Engine Build (Mode: {mode}, Target: {target})...")
            self._update_dashboard_state(project_id, "RESEARCH", f"Applying {mode} strategies to: {goal}", mode, target)
            
            # We could run this in a thread to update state more granularly, 
            # but for now we'll do blocking calls and update major milestones.
            if mode == "reverse" and source_path:
                self._update_dashboard_state(project_id, "DECOMPILE", f"Decompiling source at {source_path}", mode, target)
            
            result = engine.run()
            success = result.get("success", False)
            
            if success:
                self._update_dashboard_state(project_id, "COMPLETE", f"{mode.capitalize()} build successful.", mode, target)
            else:
                self._update_dashboard_state(project_id, "FAILED", "Engine encountered an unrecoverable error.", mode, target)


            return success, result.get("project_path", f"applications/{project_id}")
            
        except Exception as e:
            print(f"BRIDGE: Advanced Engine Error: {e}")
            self._update_dashboard_state(project_id, "FAILED", f"Bridge error: {str(e)}", mode, target)
            return False, str(e)

creation_engine = CreationEngineBridge()
