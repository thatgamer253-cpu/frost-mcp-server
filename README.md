# Frost Job Tools

AI-powered job scanning and cover letter generation for job seekers.

## Features

- **Job Scanning**: Scan Upwork and LinkedIn for opportunities matching your keywords
- **Cover Letter Generation**: Generate professional, AI-powered cover letters customized to specific jobs
- **API Access**: Simple REST API for easy integration

## Tools

### scan_jobs

Scan job boards for opportunities matching keywords. Returns job listings with titles, companies, descriptions, and URLs.

**Endpoint**: `POST /tools/scan_jobs`

**Parameters**:

- `keywords` (array): Keywords to search for (e.g., ["Python Developer", "AI Engineer"])
- `platforms` (array): Platforms to scan (options: "upwork", "linkedin")
- `api_key` (string): Your Frost API key

**Cost**: $0.10 per scan

### generate_cover_letter

Generate a professional cover letter customized to a specific job posting.

**Endpoint**: `POST /tools/generate_cover_letter`

**Parameters**:

- `job_title` (string): The job title
- `job_description` (string): The full job description
- `company` (string): The company name
- `api_key` (string): Your Frost API key

**Cost**: $0.50 per letter

## Installation

### For Claude Desktop

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
        "https://frost-mcp-server-1.onrender.com"
      ]
    }
  }
}
```

### For Developers

```python
import requests

# Scan jobs
response = requests.post(
    "https://frost-mcp-server-1.onrender.com/tools/scan_jobs",
    json={
        "keywords": ["Python Developer"],
        "platforms": ["upwork", "linkedin"],
        "api_key": "your-api-key"
    }
)

# Generate cover letter
response = requests.post(
    "https://frost-mcp-server-1.onrender.com/tools/generate_cover_letter",
    json={
        "job_title": "AI Engineer",
        "job_description": "...",
        "company": "Acme Corp",
        "api_key": "your-api-key"
    }
)
```

## Getting an API Key

1. Visit https://frost-mcp-server-1.onrender.com
2. Sign up for an account
3. Choose a plan:
   - **Free**: 5 scans/month, 2 letters/month
   - **Pro**: $10/month - Unlimited scans, 50 letters
   - **Enterprise**: $50/month - Unlimited everything

## API Documentation

Interactive API docs: https://frost-mcp-server-1.onrender.com/docs

## Source Code

GitHub: https://github.com/thatgamer253-cpu/frost-mcp-server

## License

MIT

## Support

For issues or questions, please open an issue on GitHub.
