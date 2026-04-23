#!/data/data/com.termux/files/usr/bin/bash
# ─────────────────────────────────────────────────────
#  PW PCB Manager — One-tap start script for Termux
#  Run this once:  bash START.sh
# ─────────────────────────────────────────────────────

set -e
cd "$(dirname "$0")"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "  ██████╗ ██╗    ██╗    ██████╗  ██████╗██████╗ "
echo "  ██╔══██╗██║    ██║    ██╔══██╗██╔════╝██╔══██╗"
echo "  ██████╔╝██║ █╗ ██║    ██████╔╝██║     ██████╔╝"
echo "  ██╔═══╝ ██║███╗██║    ██╔═══╝ ██║     ██╔══██╗"
echo "  ██║     ╚███╔███╔╝    ██║     ╚██████╗██████╔╝"
echo "  ╚═╝      ╚══╝╚══╝     ╚═╝      ╚═════╝╚═════╝ "
echo -e "${NC}"
echo -e "${CYAN}  Physics Wallah PCB Content Manager${NC}"
echo ""

# ── Step 1: Pull latest code ──────────────────────────────────────────────
echo -e "${YELLOW}[1/6] Pulling latest code...${NC}"
git pull origin claude/pw-pcb-updates-app-bNCnt 2>/dev/null || echo "  (already up to date or no network)"

# ── Step 2: Install Python packages ──────────────────────────────────────
echo -e "${YELLOW}[2/6] Installing Python packages...${NC}"
pip install -q -r requirements.txt && echo -e "  ${GREEN}✓ Packages ready${NC}"

# ── Step 3: Create .env if missing ───────────────────────────────────────
echo -e "${YELLOW}[3/6] Checking .env file...${NC}"
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "  ${YELLOW}⚠ Created .env from template.${NC}"
    echo ""
    echo -e "  ${RED}IMPORTANT: Fill in your API keys in .env${NC}"
    echo "  Required for Telegram: TELEGRAM_API_ID + TELEGRAM_API_HASH"
    echo "  Get them at: https://my.telegram.org/apps"
    echo ""
    echo -e "  For Instagram posting: INSTAGRAM_USERNAME + INSTAGRAM_PASSWORD"
    echo ""
    read -p "  Press ENTER to open .env in nano (Ctrl+X to save)..."
    nano .env
else
    echo -e "  ${GREEN}✓ .env exists${NC}"
fi

# ── Step 4: Check Telegram session ───────────────────────────────────────
echo -e "${YELLOW}[4/6] Checking Telegram session...${NC}"
source .env 2>/dev/null || true
if [ -z "$TELEGRAM_API_ID" ] || [ "$TELEGRAM_API_ID" = "your_telegram_api_id" ]; then
    echo -e "  ${YELLOW}⚠ Telegram not configured (TELEGRAM_API_ID missing)${NC}"
    echo "    Telegram collection will be skipped."
    echo "    Add TELEGRAM_API_ID + TELEGRAM_API_HASH to .env to enable it."
else
    SESSION_FILE=$(ls *.session 2>/dev/null | head -1)
    if [ -z "$SESSION_FILE" ]; then
        echo -e "  ${YELLOW}⚠ No Telegram session found — running setup...${NC}"
        python scripts/setup_telegram.py
    else
        echo -e "  ${GREEN}✓ Telegram session found: $SESSION_FILE${NC}"
    fi
fi

# ── Step 5: Initialize database ──────────────────────────────────────────
echo -e "${YELLOW}[5/6] Initializing database...${NC}"
python -c "
from app import create_app
app = create_app()
print('  DB ready')
" && echo -e "  ${GREEN}✓ Database ready with all default sources${NC}"

# ── Step 6: Start the app ─────────────────────────────────────────────────
echo ""
echo -e "${GREEN}[6/6] Starting PW PCB Manager...${NC}"
echo ""
echo -e "  ${CYAN}Dashboard → http://localhost:5000${NC}"
echo -e "  ${CYAN}On your phone browser → http://127.0.0.1:5000${NC}"
echo ""
echo "  Tips:"
echo "  • Click 'Collect Now' to fetch updates from all 50+ sources"
echo "  • Star important updates, then Promote → generates image + caption"
echo "  • In editor: pick Hype/Educational/Funny style → Regen caption"
echo "  • 'Post Now' posts directly to Instagram (if credentials set)"
echo ""
echo -e "${YELLOW}  Press Ctrl+C to stop the server${NC}"
echo ""
python run.py
