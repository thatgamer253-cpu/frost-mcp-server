# Quick Deploy to Render.com

Since Railway CLI is blocked, we'll use **Render** which has a simple web UI.

## Step 1: Create Account

Go to https://render.com and sign up (free).

## Step 2: Create New Web Service

1. Click "New +" → "Web Service"
2. Choose "Deploy from GitHub" OR "Upload files"

## Step 3: Upload These Files

If using "Upload files", zip and upload:

- `frost_mcp_server.py`
- `api_key_manager.py`
- `scanner.py`
- `generator.py`
- `revenue.py`
- `requirements.txt`
- `Procfile`

## Step 4: Configure Service

- **Name**: `frost-mcp-server`
- **Environment**: Python 3
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python frost_mcp_server.py`
- **Plan**: Free

## Step 5: Add Environment Variables

In Render dashboard, add:

- `OPENAI_API_KEY` = your OpenAI key
- `STRIPE_SECRET_KEY` = your Stripe key (optional for now)

## Step 6: Deploy

Click "Create Web Service" and wait 2-3 minutes.

## Step 7: Get Your URL

You'll get a URL like: `https://frost-mcp-server.onrender.com`

## Step 8: Test

```bash
curl https://frost-mcp-server.onrender.com/health
```

## Next: Publish to MCP Directory

Once deployed, submit to https://github.com/modelcontextprotocol/servers

---

**Alternative: I can create a GitHub repo for you**

This makes deployment even easier:

1. I create a GitHub repo with all files
2. You connect it to Render
3. Auto-deploys on every push

Want me to do that instead?
