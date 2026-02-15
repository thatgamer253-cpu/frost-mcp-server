# Frost MCP Server

AI-powered job scanning and cover letter generation tools for AI agents.

## Tools

- **scan_jobs**: Scan Upwork and LinkedIn for job opportunities
- **generate_cover_letter**: Generate professional, customized cover letters

## For Users

### Installation

Add to your Claude Desktop config:

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**Mac**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "frost-job-tools": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-fetch",
        "https://frost-mcp-server.onrender.com"
      ]
    }
  }
}
```

### Get API Key

1. Visit https://frost-mcp-server.onrender.com
2. Purchase access (free tier available)
3. Use your API key with the tools

## Pricing

- **Free**: 5 scans/month, 2 letters/month
- **Pro**: $10/month - Unlimited scans, 50 letters
- **Enterprise**: $50/month - Unlimited everything

## For Developers

### Local Development

```bash
pip install -r requirements.txt
python frost_mcp_server.py
```

### Deploy

See [DEPLOY.md](DEPLOY.md) for deployment instructions.

## License

MIT
