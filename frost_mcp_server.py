
import os
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Route, Mount
import uvicorn
from mcp.types import Tool, TextContent

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
        Mount("/messages", app=handle_messages), # Corrected Mount usage for Starlette
    ]
)

# Correction for handle_messages - Starlette Mount expects an ASGI app or a callable that behaves like one. 
# But handle_messages is an async function taking request. 
# Actually, sse.handle_post_message is designed for this. 
# Let's double check standard Starlette usage. 
# Route handles Http, Mount handles sub-apps. 
# If handle_messages is an endpoint, Route is correct. 
# The user's snippet used Mount("/messages", endpoint=handle_messages). 
# But usually Mount is for sub-applications. 
# Wait, the user's snippet had: Mount("/messages", endpoint=handle_messages).
# Let's stick to the user's snippet as much as possible but fix the obvious "endpoint" arg in Mount if it's wrong.
# In Starlette, Mount(path, app=...). 
# The user provided `Mount("/messages", endpoint=handle_messages)`. 
# This looks like mixing Route and Mount. 
# If `handle_messages` handles the POST request, it should be a Route. 
# I will use Route for /messages as well, as it is a single endpoint. 
# Wait, sse.handle_post_message might need to handle sub-paths? No, usually just /messages.
# I will stick to Route for both to be safe, as handle_messages is a function.

starlette_app = Starlette(
    routes=[
        Route("/sse", endpoint=handle_sse),
        Route("/messages", endpoint=handle_messages, methods=["POST"]),
    ]
)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    uvicorn.run(starlette_app, host="0.0.0.0", port=port)
