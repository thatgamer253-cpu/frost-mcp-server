import os
from typing import Optional, Dict, Any
from engine_core import NexusEngine, BuildConfig

class ToolGenerator:
    """
    Specialized wrapper for NexusEngine that focuses on generating 
    small, on-demand utilities for the Frost platform.
    """
    def __init__(self, output_base_dir: str):
        self.output_base_dir = output_base_dir

    def generate_util(self, tool_description: str, tool_name: str) -> Dict[str, Any]:
        """
        Uses NexusEngine to generate a targeted tool based on description.
        """
        project_dir = os.path.join(self.output_base_dir, tool_name)
        
        config = BuildConfig(
            project_name=tool_name,
            model="gpt-4o", # Default to gpt-4o for high-quality single-file tools
            output_dir=project_dir,
            budget=1.0,
            platform="python",
            docker=False, # Default to host for simplicity
            auto_execute=True
        )

        engine = NexusEngine(
            project_name=config.project_name,
            model=config.model,
            output_dir=config.output_dir,
            budget=config.budget,
            platform=config.platform,
            use_docker=config.docker,
            auto_execute=config.auto_execute
        )

        print(f"[FROST] Generating tool '{tool_name}' in {project_dir}...")
        result = engine.run_full_build(tool_description)
        
        return {
            "status": "success" if result else "error",
            "path": project_dir,
            "metadata": result
        }

if __name__ == "__main__":
    # Test tool generation
    gen = ToolGenerator(os.path.join(os.getcwd(), "frost_tools"))
    # gen.generate_util("Create a simple CSV to JSON converter", "csv_converter")
