#!/usr/bin/env bash
#
# ═══════════════════════════════════════════════════════════════
#  Warehouse Inventory Dashboard — One-Command Setup
# ═══════════════════════════════════════════════════════════════
#
#  Usage:  chmod +x setup.sh && ./setup.sh
#
#  This script:
#    1. Copies .env.example → .env (if needed)
#    2. Builds and starts all Docker containers
#    3. Waits for the backend to be healthy
#    4. Seeds the database with demo data
#    5. Opens the dashboard URL
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Colors ────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color
BOLD='\033[1m'

echo -e "${CYAN}${BOLD}"
echo "  ╔═══════════════════════════════════════════╗"
echo "  ║   📦 Warehouse Inventory Dashboard        ║"
echo "  ║   Setting up your environment...          ║"
echo "  ╚═══════════════════════════════════════════╝"
echo -e "${NC}"

# ── Step 1: Environment File ─────────────────────────────────
echo -e "${BLUE}[1/4]${NC} Checking environment configuration..."
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "  ${GREEN}✓${NC} Created .env from .env.example"
    else
        echo -e "  ${YELLOW}⚠${NC} No .env.example found, using defaults"
    fi
else
    echo -e "  ${GREEN}✓${NC} .env already exists"
fi

# ── Step 2: Docker Check ─────────────────────────────────────
echo -e "${BLUE}[2/4]${NC} Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo -e "  ${RED}✗ Docker is not installed.${NC}"
    echo "    Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "  ${RED}✗ Docker Compose is not installed.${NC}"
    echo "    Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi
echo -e "  ${GREEN}✓${NC} Docker is available"

# Determine docker compose command
if docker compose version &> /dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

# ── Step 3: Build and Start ──────────────────────────────────
echo -e "${BLUE}[3/4]${NC} Building and starting containers..."
echo ""
$COMPOSE_CMD up --build -d

echo ""
echo -e "  ${GREEN}✓${NC} Containers started"

# ── Step 4: Wait for Backend & Seed ──────────────────────────
echo -e "${BLUE}[4/4]${NC} Waiting for backend to be ready..."

BACKEND_URL="http://localhost:${BACKEND_PORT:-8000}"
MAX_RETRIES=30
RETRY=0

while [ $RETRY -lt $MAX_RETRIES ]; do
    if curl -s "${BACKEND_URL}/" > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} Backend is healthy"
        break
    fi
    RETRY=$((RETRY + 1))
    echo -e "  ${YELLOW}...${NC} Waiting (${RETRY}/${MAX_RETRIES})"
    sleep 2
done

if [ $RETRY -eq $MAX_RETRIES ]; then
    echo -e "  ${RED}✗ Backend did not start in time${NC}"
    echo "    Check logs: $COMPOSE_CMD logs backend"
    exit 1
fi

# Seed the database
echo -e "  ${CYAN}→${NC} Seeding database with demo data..."
SEED_RESPONSE=$(curl -s -X POST "${BACKEND_URL}/seed")
echo -e "  ${GREEN}✓${NC} Database seeded: ${SEED_RESPONSE}"

# ── Done! ─────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}  ╔═══════════════════════════════════════════╗"
echo "  ║   ✅ Setup Complete!                      ║"
echo "  ╠═══════════════════════════════════════════╣"
echo "  ║                                           ║"
echo "  ║   Dashboard:  http://localhost:3000        ║"
echo "  ║   API:        http://localhost:8000        ║"
echo "  ║   API Docs:   http://localhost:8000/docs   ║"
echo "  ║                                           ║"
echo "  ╚═══════════════════════════════════════════╝"
echo -e "${NC}"

# Try to open browser (optional, won't fail)
if command -v xdg-open &> /dev/null; then
    xdg-open "http://localhost:3000" 2>/dev/null || true
elif command -v open &> /dev/null; then
    open "http://localhost:3000" 2>/dev/null || true
fi
