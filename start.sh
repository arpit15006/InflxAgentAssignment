#!/bin/bash

# ============================================================
# AutoStream Agent - Start Both Servers
# Starts backend (FastAPI) and frontend (React/Vite) servers
# ============================================================

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  AutoStream Agent - Starting Development Servers${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Function to cleanup processes on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down servers...${NC}"
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null
    echo -e "${GREEN}Servers stopped.${NC}"
    exit 0
}

# Trap SIGINT and SIGTERM to cleanup
trap cleanup SIGINT SIGTERM

# ============================================================
# Start Backend Server
# ============================================================
echo -e "${BLUE}[1/2] Starting Backend Server (FastAPI)...${NC}"
echo -e "${YELLOW}Backend will run on: http://localhost:8000${NC}"
echo ""

cd "$PROJECT_ROOT/backend"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}Error: Virtual environment not found in backend/venv${NC}"
    echo -e "${YELLOW}Please create it first: cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt${NC}"
    exit 1
fi

# Start backend in background
"$PROJECT_ROOT/backend/venv/bin/python" -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 2

# Check if backend is running
if kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${GREEN}✓ Backend server started successfully (PID: $BACKEND_PID)${NC}"
else
    echo -e "${RED}✗ Failed to start backend server${NC}"
    exit 1
fi

echo ""

# ============================================================
# Start Frontend Server
# ============================================================
echo -e "${BLUE}[2/2] Starting Frontend Server (Vite/React)...${NC}"
echo -e "${YELLOW}Frontend will run on: http://localhost:5173${NC}"
echo ""

cd "$PROJECT_ROOT/frontend"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing frontend dependencies...${NC}"
    npm install
fi

# Start frontend in background
npm run dev &
FRONTEND_PID=$!

# Wait a moment for frontend to start
sleep 2

# Check if frontend is running
if kill -0 $FRONTEND_PID 2>/dev/null; then
    echo -e "${GREEN}✓ Frontend server started successfully (PID: $FRONTEND_PID)${NC}"
else
    echo -e "${RED}✗ Failed to start frontend server${NC}"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

echo ""
echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}  All servers are running!${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo -e "${BLUE}Frontend:${NC} http://localhost:5173"
echo -e "${BLUE}Backend API:${NC} http://localhost:8000"
echo -e "${BLUE}API Docs:${NC} http://localhost:8000/docs"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all servers${NC}"
echo ""

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
