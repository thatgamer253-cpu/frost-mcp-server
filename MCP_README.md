# Frost MCP Server - Setup Guide

## What is This?

An **MCP (Model Context Protocol) server** that exposes Frost's job scanning and cover letter generation as tools that AI agents can discover and use.

## For Users (AI Agent Operators)

### Installation

1. **Get an API Key**
   - Visit the Frost Marketplace (run `python marketplace_api.py`)
   - Purchase access to the services you want
   - Save your API key

2. **Add to Claude Desktop**

   Edit your Claude Desktop config file:
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
   - **Mac**: `~/Library/Application Support/Claude/claude_desktop_config.json`

   Add this server:

   ```json
   {
     "mcpServers": {
       "frost-job-tools": {
         "command": "python",
         "args": ["c:\\Users\\thatg\\Desktop\\Frost\\frost_mcp_server.py"]
       }
     }
   }
   ```

3. **Restart Claude Desktop**

4. **Use the Tools**

   In Claude, you can now:

   ```
   Scan Upwork and LinkedIn for "Python Developer" jobs
   ```

   ```
   Generate a cover letter for this job: [paste job description]
   ```

## Available Tools

### 1. scan_jobs

- **Description**: Scan job boards for opportunities
- **Platforms**: Upwork, LinkedIn
- **Cost**: $0.10 per scan (or included in monthly subscription)
- **Parameters**:
  - `keywords`: Array of search terms
  - `platforms`: Which platforms to scan
  - `api_key`: Your Frost API key

### 2. generate_cover_letter

- **Description**: Generate professional cover letters
- **Cost**: $0.50 per letter (or included in monthly subscription)
- **Parameters**:
  - `job_title`: The job title
  - `job_description`: Full job description
  - `company`: Company name
  - `api_key`: Your Frost API key

## Pricing

- **Pay-per-use**: $0.10/scan, $0.50/letter
- **Pro**: $10/month - Unlimited scans, 50 letters
- **Enterprise**: $50/month - Unlimited everything

## For Developers (Running the Server)

```bash
cd c:\Users\thatg\Desktop\Frost
python frost_mcp_server.py
```

The server runs via stdio and communicates using the MCP protocol.

## Troubleshooting

**"API key required"**

- Get a key from the Frost Marketplace

**"Invalid API key"**

- Your key may have expired (monthly subscriptions)
- Purchase access to the specific service

**Tools not showing in Claude**

- Restart Claude Desktop
- Check config file path
- Verify Python path in config

## Support

For issues or questions, contact support or check the documentation.
