import os
import asyncio
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse

# --- SERVER CORE ---
app_name = "frost-mcp-server"
mcp_server = Server(app_name)

# Lazy-loading state
_creation_engine_loaded = False
agents = {}

async def ensure_agents_loaded():
    global _creation_engine_loaded, agents
    if not _creation_engine_loaded:
        try:
            # Shift to Sovereign high-fidelity imports
            from creation_engine import orchestrator, architect
            agents['orchestrator'] = orchestrator
            agents['architect'] = architect
            print(f"[{app_name}] Sovereign Agents Synchronized.")
        except ImportError as e:
            print(f"[{app_name}] Agent Load Warning: {e}")
        _creation_engine_loaded = True

# --- TOOL REGISTRY ---
@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="modernize_legacy_assets",
            description="Upscale and optimize game assets using v2026 Sovereign standards.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the asset file/directory"},
                    "fidelity_level": {"type": "string", "enum": ["standard", "sovereign", "extreme"], "default": "sovereign"}
                },
                "required": ["path"]
            }
        )
    ]

@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    await ensure_agents_loaded()
    if name == "modernize_legacy_assets":
        path = arguments.get("path")
        fidelity = arguments.get("fidelity_level", "sovereign")
        return [TextContent(type="text", text=f"Alchemist: Synthesizing {path} at {fidelity} fidelity...")]
    raise ValueError(f"Tool not found: {name}")

# --- SSE TRANSPORT LAYER ---
sse = SseServerTransport("/messages")

async def handle_sse(request):
    async with sse.connect_sse(request.scope, request.receive, request._send) as (read_stream, write_stream):
        await mcp_server.run(read_stream, write_stream, mcp_server.create_initialization_options())

async def handle_messages(request):
    await sse.handle_post_message(request.scope, request.receive, request._send)

# --- STARLETTE ASGI APP ---
starlette_app = Starlette(
    routes=[
        Route("/sse", endpoint=handle_sse),
        Route("/messages", endpoint=handle_messages, methods=["POST"]),
        Route("/", endpoint=lambda r: JSONResponse({"status": "Frost MCP Online", "protocol": "SSE"}), methods=["GET"])
    ]
)

if __name__ == "__main__":
    import uvicorn
    # Render provides PORT env variable
    port = int(os.getenv("PORT", 10000))
    # Note: Use starlette_app as the ASGI target
    uvicorn.run(starlette_app, host="0.0.0.0", port=port)
