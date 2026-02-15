# Deploy to Render - Step by Step

## Your GitHub Repo

✅ https://github.com/thatgamer253-cpu/frost-mcp-server

## Deployment Steps

### 1. Go to Render

Visit: https://render.com

### 2. Sign Up/Login

- Use GitHub to sign in (easiest)
- Or create account with email

### 3. Create New Web Service

- Click "New +" button (top right)
- Select "Web Service"

### 4. Connect Repository

- Choose "Connect a repository"
- Find: `thatgamer253-cpu/frost-mcp-server`
- Click "Connect"

### 5. Configure Service

Fill in these settings:

**Name:** `frost-mcp-server`

**Region:** Oregon (US West) - free tier

**Branch:** `main`

**Root Directory:** (leave blank)

**Runtime:** Python 3

**Build Command:**

```
bash render-build.sh
```

**Start Command:**

```
python frost_mcp_server.py
```

**Instance Type:** Free

### 6. Environment Variables

Click "Advanced" and add:

- Key: `OPENAI_API_KEY`
- Value: Your OpenAI API key

(Stripe key optional for now)

### 7. Deploy!

- Click "Create Web Service"
- Wait 2-3 minutes for deployment
- You'll get a URL like: `https://frost-mcp-server.onrender.com`

### 8. Test It

```bash
curl https://frost-mcp-server.onrender.com
```

## After Deployment

### Update README

Add your live URL to the README on GitHub

### Submit to MCP Directory

1. Fork: https://github.com/modelcontextprotocol/servers
2. Add your server to the registry
3. Submit PR

### Market It

- Post on r/ClaudeAI
- Share in AI communities
- Offer free tier

## You're Live!

Real users can now discover and use your tools → you earn money!
