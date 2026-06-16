#!/bin/bash
# FormatIQ — one-command startup

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════╗${NC}"
echo -e "${BLUE}║   FormatIQ — YouTube Research    ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════╝${NC}"
echo ""

# Check Python
if ! command -v python3 &>/dev/null && ! command -v python &>/dev/null; then
  echo "❌ Python not found. Please install Python 3.10+"
  exit 1
fi
PYTHON=$(command -v python3 || command -v python)

# Check Node
if ! command -v node &>/dev/null; then
  echo "❌ Node.js not found. Please install Node.js 18+"
  exit 1
fi

# Install backend dependencies
echo -e "${YELLOW}→ Installing Python dependencies...${NC}"
cd "$BACKEND_DIR"
if [ ! -d "venv" ]; then
  $PYTHON -m venv venv
fi
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null
pip install -q -r "$SCRIPT_DIR/requirements.txt"

# Install frontend dependencies
echo -e "${YELLOW}→ Installing Node dependencies...${NC}"
cd "$FRONTEND_DIR"
if [ ! -d "node_modules" ]; then
  npm install --silent
fi

# Start backend
echo -e "${GREEN}→ Starting backend on http://localhost:8000${NC}"
cd "$BACKEND_DIR"
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait for backend to be ready
sleep 2

# Start frontend
echo -e "${GREEN}→ Starting frontend on http://localhost:5173${NC}"
cd "$FRONTEND_DIR"
npm run dev &
FRONTEND_PID=$!

echo ""
echo -e "${GREEN}✅ FormatIQ is running!${NC}"
echo -e "   Frontend: ${BLUE}http://localhost:5173${NC}"
echo -e "   Backend:  ${BLUE}http://localhost:8000${NC}"
echo -e "   API docs: ${BLUE}http://localhost:8000/docs${NC}"
echo ""
echo "Press Ctrl+C to stop both servers."

# Cleanup on exit
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Stopped.'" EXIT INT TERM
wait
