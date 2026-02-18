
import os
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP - This automatically handles the ASGI app conversion
mcp = FastMCP("frost-mcp-server")

# --- Creation Engine Tools ---

@mcp.tool()
async def modernize_assets(path: str):
    """
    Trigger the Alchemist to upscale and optimize game assets.
    """
    return f"Alchemist: Starting 4K upscale on {path}. Check local 3060 Ti logs."

@mcp.tool()
async def run_siege_benchmark(target_exe: str):
    """
    Trigger the Sentinel to run a performance stress test.
    """
    return f"Sentinel: Initiating siege test on {target_exe}. Monitoring VRAM..."

# --- Deployment Logic ---

if __name__ == "__main__":
    # When running on Render, FastMCP needs to run as an SSE server
    port = int(os.getenv("PORT", 10000))
    # 'host' must be 0.0.0.0 for Render to see the traffic
    mcp.run(transport="sse", host="0.0.0.0", port=port)
