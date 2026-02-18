
import os
import sys
import subprocess

# --- SELF-HEALING IMPORT LOGIC ---
try:
    from mcp.server import Server
except ImportError:
    print("⚠️  MCP module not found. Attempting emergency runtime installation...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "mcp"])
        from mcp.server import Server
        print("✅  Emergency install successful. Resuming startup.")
    except Exception as e:
        print(f"❌  Critical Error: Failed to install mcp. {e}")
        # Re-raise to crash properly if we can't fix it
        raise

# Import the rest after ensuring mcp exists
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent
from starlette.applications import Starlette
from starlette.routing import Route
import uvicorn

# 1. Initialize the MCP Server
app = Server("frost-mcp-server")

# 2. Define your tools
@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="modernize_assets",
            description="Trigger the Alchemist for OSRS 4K upscaling.",
            inputSchema={"type": "object", "properties": {"path": {"type": "string"}}}
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    return [TextContent(type="text", text=f"Success: {name} triggered for {arguments.get('path')}")]

# 3. Setup the SSE Transport logic for Render
sse = SseServerTransport("/messages")

async def handle_sse(request):
    async with sse.connect_sse(request.scope, request.receive, request._send) as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

async def handle_messages(request):
    await sse.handle_post_message(request.scope, request.receive, request._send)

# 4. Create the Starlette App (The "Callable" Render wants)
starlette_app = Starlette(
    routes=[
        Route("/sse", endpoint=handle_sse),
        Route("/messages", endpoint=handle_messages, methods=["POST"]),
    ]
)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    uvicorn.run(starlette_app, host="0.0.0.0", port=port)
