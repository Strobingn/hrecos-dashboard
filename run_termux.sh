#!/data/data/com.termux/files/usr/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# HRECOS Dashboard — Termux Run Script
# Tested on Android Termux with Python 3.11+
# ─────────────────────────────────────────────────────────────────────────────

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🌊 HRECOS Dashboard — Termux Mode"
echo ""

# ── Termux package check ───────────────────────────────────────────────────
if ! command -v python &>/dev/null && ! command -v python3 &>/dev/null; then
    echo "📦 Installing Python via pkg..."
    pkg install python -y
fi

PYTHON=$(command -v python3 || command -v python)
PIP=$(command -v pip3 || command -v pip)

echo "✅ Python: $($PYTHON --version)"

# Termux needs libxml2 and libxslt for some deps — install if missing
if ! pkg list-installed 2>/dev/null | grep -q "libxml2"; then
    echo "📦 Installing system deps..."
    pkg install libxml2 libxslt openssl -y 2>/dev/null || true
fi

# ── Python deps ────────────────────────────────────────────────────────────
if ! $PYTHON -c "import fastapi" &>/dev/null; then
    echo "📦 Installing Python dependencies..."
    echo "   (pre-built wheels only — should be fast)"
    $PIP install --upgrade pip 2>/dev/null
    $PIP install -r requirements-termux.txt --prefer-binary
fi

# ── Environment ────────────────────────────────────────────────────────────
export DATABASE_URL="sqlite+aiosqlite:////${SCRIPT_DIR}/hrecos.db"
export EMAIL_ENABLED=false
export SMS_ENABLED=false
export SLACK_ENABLED=false

# Detect local IP for LAN access
LOCAL_IP=$(ip route get 1 2>/dev/null | awk '{print $7; exit}' || echo "localhost")

echo ""
echo "✅ SQLite database: ${SCRIPT_DIR}/hrecos.db"
echo ""
echo "📡 Backend:  http://localhost:8000"
echo "🖥️  Frontend: http://localhost:8080"
echo ""
echo "📱 On your local network:"
echo "   http://${LOCAL_IP}:8080"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# ── Start backend ──────────────────────────────────────────────────────────
cd "$SCRIPT_DIR/backend"
$PYTHON -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --no-access-log &
BACKEND_PID=$!

# Wait for backend to be ready
echo "⏳ Waiting for backend..."
for i in $(seq 1 15); do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ Backend ready"
        break
    fi
    sleep 1
done

# ── Start frontend ─────────────────────────────────────────────────────────
cd "$SCRIPT_DIR/frontend"
$PYTHON -m http.server 8080 --bind 0.0.0.0 &
FRONTEND_PID=$!

echo "✅ Frontend ready"
echo ""
echo "🌊 Dashboard running. Open your browser to http://localhost:8080"
echo ""

trap "echo ''; echo 'Stopping...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM
wait $BACKEND_PID
