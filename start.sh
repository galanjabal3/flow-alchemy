#!/bin/bash

# FlowAlchemy — Start both backend & frontend
# Usage: ./start.sh          (start both)
#        ./start.sh stop     (stop both)
#        ./start.sh status   (check status)

BACKEND_DIR="$(dirname "$0")/backend"
FRONTEND_DIR="$(dirname "$0")/frontend"
BACKEND_LOG="/tmp/flowalchemy-backend.log"
FRONTEND_LOG="/tmp/flowalchemy-frontend.log"
WORKER_LOG="/tmp/flowalchemy-worker.log"
BACKEND_PID_FILE="/tmp/flowalchemy-backend.pid"
FRONTEND_PID_FILE="/tmp/flowalchemy-frontend.pid"
WORKER_PID_FILE="/tmp/flowalchemy-worker.pid"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

stop_servers() {
    echo -e "${YELLOW}Stopping servers...${NC}"
    if [ -f "$BACKEND_PID_FILE" ]; then
        kill $(cat "$BACKEND_PID_FILE") 2>/dev/null
        rm -f "$BACKEND_PID_FILE"
    fi
    if [ -f "$FRONTEND_PID_FILE" ]; then
        kill $(cat "$FRONTEND_PID_FILE") 2>/dev/null
        rm -f "$FRONTEND_PID_FILE"
    fi
    if [ -f "$WORKER_PID_FILE" ]; then
        kill $(cat "$WORKER_PID_FILE") 2>/dev/null
        rm -f "$WORKER_PID_FILE"
    fi
    # Safety net: kill any orphaned worker (e.g. leftover from a stale pid file)
    pkill -f "python -m app.worker" 2>/dev/null
    kill -9 $(lsof -ti:8000) 2>/dev/null
    kill -9 $(lsof -ti:5173) 2>/dev/null
    echo -e "${GREEN}Stopped.${NC}"
}

status_servers() {
    echo -e "${YELLOW}Checking status...${NC}"
    if lsof -ti:8000 > /dev/null 2>&1; then
        echo -e "Backend:  ${GREEN}RUNNING${NC} → http://localhost:8000"
    else
        echo -e "Backend:  ${RED}STOPPED${NC}"
    fi
    if lsof -ti:5173 > /dev/null 2>&1; then
        echo -e "Frontend: ${GREEN}RUNNING${NC} → http://localhost:5173"
    else
        echo -e "Frontend: ${RED}STOPPED${NC}"
    fi
    if pgrep -f "python -m app.worker" > /dev/null 2>&1; then
        echo -e "Worker:   ${GREEN}RUNNING${NC} (processes execution jobs)"
    else
        echo -e "Worker:   ${RED}STOPPED${NC}"
    fi
}

start_servers() {
    stop_servers

    echo -e "${YELLOW}Starting FlowAlchemy...${NC}"

    # Backend
    cd "$BACKEND_DIR"
    source .venv/bin/activate
    nohup python run.py > "$BACKEND_LOG" 2>&1 &
    echo $! > "$BACKEND_PID_FILE"
    cd - > /dev/null

    # Worker (processes queued executions — required for Run to work locally)
    cd "$BACKEND_DIR"
    source .venv/bin/activate
    nohup python -m app.worker > "$WORKER_LOG" 2>&1 &
    echo $! > "$WORKER_PID_FILE"
    cd - > /dev/null

    # Frontend
    cd "$FRONTEND_DIR"
    nohup npm run dev > "$FRONTEND_LOG" 2>&1 &
    echo $! > "$FRONTEND_PID_FILE"
    cd - > /dev/null

    sleep 3

    echo ""
    echo -e "${GREEN}FlowAlchemy is running!${NC}"
    echo ""
    echo "  Backend API:   http://localhost:8000"
    echo "  Swagger Docs:  http://localhost:8000/docs"
    echo "  Frontend App:  http://localhost:5173"
    echo ""
    echo "  Logs:"
    echo "    Backend:  $BACKEND_LOG"
    echo "    Worker:   $WORKER_LOG"
    echo "    Frontend: $FRONTEND_LOG"
    echo ""
    echo "  Stop with: ./start.sh stop"
}

case "${1}" in
    stop)
        stop_servers
        ;;
    status)
        status_servers
        ;;
    *)
        start_servers
        ;;
esac
