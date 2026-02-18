import os
import subprocess
import json
from ..llm_client import log

class ShortsValidator:
    """Verifies that the generated video meets the 'Shorts' criteria: 9:16 aspect ratio and >= 1080p resolution."""

    def __init__(self, target_path: str):
        self.target_path = target_path

    def validate(self) -> dict:
        """Runs ffprobe to check resolution and aspect ratio."""
        if not os.path.exists(self.target_path):
            return {"success": False, "error": f"File not found: {self.target_path}"}

        try:
            cmd = [
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_streams", "-show_format", self.target_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            data = json.loads(result.stdout)

            video_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
            if not video_stream:
                return {"success": False, "error": "No video stream found."}

            width = int(video_stream.get("width", 0))
            height = int(video_stream.get("height", 0))
            
            # Check aspect ratio (9:16 approx 0.5625)
            actual_ratio = width / height if height > 0 else 0
            is_vertical = actual_ratio < 1.0 and 0.5 < actual_ratio < 0.6
            
            # Check resolution (1080p minimum height 1920)
            is_high_res = height >= 1920

            log("SUPERVISOR", f"  Checking Specs: {width}x{height} (Ratio: {actual_ratio:.4f})")

            issues = []
            if not is_vertical:
                issues.append(f"Aspect ratio is not 9:16 (Found {width}:{height})")
            if not is_high_res:
                issues.append(f"Resolution is below 1080p (Found {height}p height)")

            if not issues:
                log("SUPERVISOR", "  ✅ Shorts Validation Passed")
                return {"success": True, "width": width, "height": height}
            else:
                for issue in issues:
                    log("WARN", f"  ✗ {issue}")
                return {"success": False, "error": "; ".join(issues)}

        except Exception as e:
            return {"success": False, "error": f"Validation failed: {str(e)}"}
