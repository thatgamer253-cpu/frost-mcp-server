"""
Frost MCP Server

Exposes job scanning and cover letter generation as MCP tools
for AI agents to discover and use.
"""

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from api_key_manager import APIKeyManager
from scanner import JobScanner
from generator import MaterialGenerator
from revenue import RevenueManager
import json
import os

# Initialize managers
key_manager = APIKeyManager()
revenue_manager = RevenueManager()

# Create MCP server
app = Server("frost-job-tools")

# Define tools
@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="scan_jobs",
            description="Scan job boards (Upwork, LinkedIn) for opportunities matching keywords. Returns job listings with titles, companies, descriptions, and URLs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Keywords to search for (e.g., ['Python Developer', 'AI Engineer'])"
                    },
                    "platforms": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["upwork", "linkedin"]},
                        "description": "Platforms to scan (default: ['upwork', 'linkedin'])",
                        "default": ["upwork", "linkedin"]
                    },
                    "api_key": {
                        "type": "string",
                        "description": "Your Frost API key (get one at https://frost-marketplace.example.com)"
                    }
                },
                "required": ["keywords", "api_key"]
            }
        ),
        Tool(
            name="generate_cover_letter",
            description="Generate a professional, AI-powered cover letter customized to a specific job posting.",
            inputSchema={
                "type": "object",
                "properties": {
                    "job_title": {
                        "type": "string",
                        "description": "The job title"
                    },
                    "job_description": {
                        "type": "string",
                        "description": "The full job description"
                    },
                    "company": {
                        "type": "string",
                        "description": "The company name"
                    },
                    "api_key": {
                        "type": "string",
                        "description": "Your Frost API key"
                    }
                },
                "required": ["job_title", "job_description", "company", "api_key"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    
    # Extract and validate API key
    api_key = arguments.get("api_key")
    if not api_key:
        return [TextContent(
            type="text",
            text="Error: API key required. Get one at https://frost-marketplace.example.com"
        )]
    
    # Validate key for the specific service
    service_map = {
        "scan_jobs": "job-scanner-api",
        "generate_cover_letter": "cover-letter-generator"
    }
    
    service_id = service_map.get(name)
    valid, message = key_manager.validate_key(api_key, service_id)
    
    if not valid:
        return [TextContent(
            type="text",
            text=f"Error: {message}. Visit https://frost-marketplace.example.com to purchase access."
        )]
    
    # Execute the tool
    if name == "scan_jobs":
        return await scan_jobs_tool(arguments)
    elif name == "generate_cover_letter":
        return await generate_cover_letter_tool(arguments)
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

async def scan_jobs_tool(args: dict) -> list[TextContent]:
    """Execute job scanning."""
    try:
        keywords = args.get("keywords", [])
        platforms = args.get("platforms", ["upwork", "linkedin"])
        
        # Create scanner
        scanner = JobScanner()
        
        # Build profile for scanning
        profile = {
            "platforms": {
                "upwork": {"enabled": "upwork" in platforms, "keywords": keywords},
                "linkedin": {"enabled": "linkedin" in platforms, "keywords": keywords}
            }
        }
        
        # Scan
        jobs = scanner.scan_all(profile)
        
        # Format results
        if not jobs:
            result = "No jobs found matching your criteria."
        else:
            result = f"Found {len(jobs)} jobs:\n\n"
            for i, job in enumerate(jobs[:10], 1):  # Limit to 10 results
                result += f"{i}. **{job['title']}** at {job['company']}\n"
                result += f"   Platform: {job['platform']}\n"
                result += f"   URL: {job['url']}\n\n"
            
            if len(jobs) > 10:
                result += f"... and {len(jobs) - 10} more jobs"
        
        # Track usage
        revenue_manager.record_marketplace_sale(
            service_id="job-scanner-api",
            service_name="Job Scanner API (MCP)",
            amount=0.10,  # $0.10 per scan
            agent_id=args.get("api_key", "unknown")[:16]
        )
        
        return [TextContent(type="text", text=result)]
        
    except Exception as e:
        return [TextContent(type="text", text=f"Error scanning jobs: {str(e)}")]

async def generate_cover_letter_tool(args: dict) -> list[TextContent]:
    """Execute cover letter generation."""
    try:
        # Load default profile
        profile_file = "profiles/ai_strategist_1771146284.json"
        if os.path.exists(profile_file):
            with open(profile_file, 'r') as f:
                profile = json.load(f)
        else:
            return [TextContent(type="text", text="Error: Profile not found")]
        
        # Create job object
        job = {
            "title": args["job_title"],
            "description": args["job_description"],
            "company": args["company"]
        }
        
        # Generate letter
        generator = MaterialGenerator(profile)
        letter = generator.generate_cover_letter(job)
        
        # Track usage
        revenue_manager.record_marketplace_sale(
            service_id="cover-letter-generator",
            service_name="Cover Letter Generator (MCP)",
            amount=0.50,  # $0.50 per letter
            agent_id=args.get("api_key", "unknown")[:16]
        )
        
        return [TextContent(type="text", text=letter)]
        
    except Exception as e:
        return [TextContent(type="text", text=f"Error generating cover letter: {str(e)}")]

async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
