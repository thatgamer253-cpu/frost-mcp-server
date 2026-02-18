import os
import asyncio
from mcp.server import Server
from mcp.types import Tool, TextContent

app = Server("frost-mcp-server")

# This flag prevents the server from crashing on startup
_engine_ready = False

async def load_creation_engine():
    global _engine_ready
    if not _engine_ready:
        # Heavily logic imports/init would go here
        _engine_ready = True

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="modernize_assets",
            description="Upscale and optimize game assets.",
            inputSchema={"type": "object", "properties": {"path": {"type": "string"}}}
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    await load_creation_engine() # Only loads when used
    return [TextContent(type="text", text=f"Engine active. Processing {arguments.get('path')}...")]

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
