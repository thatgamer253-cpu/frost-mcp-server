# GitHub Authentication Fix

## The Issue

Git is trying to use the wrong GitHub account (SirSilth253 instead of thatgamer253-cpu).

## Quick Fix Options

### Option 1: Use GitHub Desktop (Easiest)

1. Download GitHub Desktop: https://desktop.github.com
2. Sign in with thatgamer253-cpu account
3. File → Add Local Repository → Select `c:\Users\thatg\Desktop\Frost`
4. Click "Publish repository"
5. Done!

### Option 2: Use Personal Access Token

1. Go to https://github.com/settings/tokens
2. Generate new token (classic)
3. Select scopes: `repo`
4. Copy the token
5. Run:
   ```bash
   git remote set-url origin https://YOUR_TOKEN@github.com/thatgamer253-cpu/frost-mcp-server.git
   git push -u origin main
   ```

### Option 3: SSH Key

1. Generate SSH key:
   ```bash
   ssh-keygen -t ed25519 -C "your_email@example.com"
   ```
2. Add to GitHub: https://github.com/settings/keys
3. Change remote to SSH:
   ```bash
   git remote set-url origin git@github.com:thatgamer253-cpu/frost-mcp-server.git
   git push -u origin main
   ```

## Recommended: GitHub Desktop

It's the easiest and handles authentication automatically.

## After Push Success

Once code is on GitHub:

1. Go to https://render.com
2. New Web Service → Connect GitHub repo
3. Deploy!
