#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# HRECOS Dashboard — Mobile / Lightweight Run Script
# No Docker, no PostgreSQL, no Twilio required.
# Uses SQLite. Runs backend + serves frontend in two commands.
# ─────────────────────────────────────────────────────────────────────────────

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🌊 HRECOS Dashboard — Mobile Mode"
echo ""

# Python check
if ! command -v python3 &>/dev/null; then
    echo "❌ python3 not found. Install Python 3.10+ first."
    exit 1
fi

# Install deps if needed
if ! python3 -c "import fastapi" &>/dev/null; then
    echo "📦 Installing dependencies..."
    pip3 install -r requirements-mobile.txt
fi

# Set SQLite env (overrides any .env PostgreSQL URL)
export DATABASE_URL="sqlite+aiosqlite:///./hrecos.db"
export EMAIL_ENABLED=false
export SMS_ENABLED=false
export SLACK_ENABLED=false

echo "✅ Using SQLite database: ./hrecos.db"
echo "✅ Alerts disabled (enable in .env if desired)"
echo ""
echo "📡 Starting backend on  http://localhost:8000"
echo "🖥️  Starting frontend on http://localhost:8080"
echo ""
echo "   Open http://localhost:8080 in your browser"
echo "   API docs at http://localhost:8000/docs"
echo ""
echo "   Press Ctrl+C to stop"
echo ""

# Start backend in background
cd backend
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Give backend a moment to start
sleep 2

# Serve frontend
cd "$SCRIPT_DIR/frontend"
python3 -m http.server 8080 &
FRONTEND_PID=$!

# Trap Ctrl+C
trap "echo ''; echo 'Stopping...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM

# Wait
wait $BACKEND_PID
