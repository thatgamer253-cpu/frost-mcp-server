import os
import sys
from bundler_agent import BundlerAgent

# Mock output directory setup from TinyTest11
output_dir = "./output"
project_name = "TinyTest11"

# Ensure dummy assets exist to test asset bundling
assets_dir = os.path.join(output_dir, project_name, "assets", "gen")
os.makedirs(assets_dir, exist_ok=True)
with open(os.path.join(assets_dir, "test_asset.txt"), "w") as f:
    f.write("This is a test asset.")

print(f"Testing Bundler for {project_name}...")
agent = BundlerAgent(output_dir)
success = agent.bundle(project_name)

if success:
    dist_path = os.path.join(output_dir, "dist")
    if os.path.exists(dist_path) and os.path.exists(os.path.join(dist_path, f"{project_name}_source.zip")):
        print("Bundling Successful!")
        sys.exit(0)
    else:
        print("Dist folder or zip missing!")
        sys.exit(1)
else:
    print("Bundler returned False")
    sys.exit(1)
