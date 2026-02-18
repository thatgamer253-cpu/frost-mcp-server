import os
import shutil

class BundlerAgent:
    """
    The Distributor.
    Packages the final 'One Hand-off' delivery for the user.
    """
    def __init__(self, output_dir):
        self.output_dir = output_dir
        self.dist_dir = os.path.join(output_dir, "dist")

    def bundle(self, project_name):
        """Creates the final distribution package."""
        print(f"[BUNDLER] Packaging '{project_name}' for delivery...")
        
        project_root = os.path.join(self.output_dir, project_name)
        if not os.path.exists(project_root):
            print(f"[BUNDLER] [ERROR] Project not found: {project_root}")
            return False

        # Create output distribution directory
        if os.path.exists(self.dist_dir):
            shutil.rmtree(self.dist_dir)
        os.makedirs(self.dist_dir, exist_ok=True)
        
        # 1. Zip the Source Code
        zip_path = os.path.join(self.dist_dir, f"{project_name}_source")
        shutil.make_archive(zip_path, 'zip', project_root)
        print(f"[BUNDLER] Source archived: {zip_path}.zip")
        
        # 2. Collect Assets (Visual DNA, Motion Proofs)
        assets_source = os.path.join(project_root, "assets", "gen")
        assets_dest = os.path.join(self.dist_dir, "assets")
        
        if os.path.exists(assets_source) and os.path.isdir(assets_source):
             # Ensure dest is clean
            if os.path.exists(assets_dest):
                shutil.rmtree(assets_dest)
            shutil.copytree(assets_source, assets_dest)
            print(f"[BUNDLER] Assets secured in /dist/assets")
        else:
            print("[BUNDLER] No generated assets found to bundle.")

        print(f"[BUNDLER] Package Ready at: {self.dist_dir}")
        return True

if __name__ == "__main__":
    # Test stub
    agent = BundlerAgent("./output")
    agent.bundle("TinyTest11")
