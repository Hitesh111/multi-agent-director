#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

usage() {
    cat <<EOF
Usage: ./run.sh [command]

Commands:
  backend      Start Django dev server (:8000)
  worker       Start Celery worker
  beat         Start Celery beat scheduler
  flower       Start Celery Flower monitor (:5555)
  bot          Start Telegram bot polling
  frontend     Start Next.js dev server (:3000)
  all          Start backend + worker + bot + frontend (concurrently)
  migrate      Run database migrations
  seed         Seed demo agents and workflow
  test         Run backend tests
  shell        Open Django shell
  db           Open PostgreSQL CLI
  redis        Open Redis CLI
  logs         Tail Docker logs
  help         Show this help

Examples:
  ./run.sh backend        # Django on :8000
  ./run.sh worker         # Celery worker
  ./run.sh all            # Everything
EOF
}

ensure_venv() {
    if [ -z "${VIRTUAL_ENV:-}" ]; then
        if [ -d .venv ]; then
            source .venv/bin/activate
        else
            echo -e "${RED}No .venv found. Run setup.sh first.${NC}"
            exit 1
        fi
    fi
}

case "${1:-help}" in
    backend)
        ensure_venv
        echo -e "${CYAN}Starting Django dev server on :8000...${NC}"
        python backend/manage.py runserver 0.0.0.0:8000
        ;;
    worker)
        ensure_venv
        echo -e "${CYAN}Starting Celery worker...${NC}"
        cd backend && celery -A config.celery worker -l info
        ;;
    beat)
        ensure_venv
        echo -e "${CYAN}Starting Celery beat...${NC}"
        cd backend && celery -A config.celery beat -l info
        ;;
    flower)
        ensure_venv
        echo -e "${CYAN}Starting Flower on :5555...${NC}"
        cd backend && celery -A config.celery flower --port=5555
        ;;
    bot)
        ensure_venv
        echo -e "${CYAN}Starting Telegram bot polling...${NC}"
        python backend/manage.py runbot
        ;;
    frontend)
        echo -e "${CYAN}Starting Next.js on :3000...${NC}"
        cd frontend && npm run dev
        ;;
    all)
        echo -e "${CYAN}Starting all services (Press Ctrl+C to stop)...${NC}"
        ensure_venv
        
        # Start processes in the background
        python backend/manage.py runserver 0.0.0.0:8000 &
        P1=$!
        
        (cd backend && celery -A config.celery worker -l info) &
        P2=$!
        
        (cd frontend && npm run dev) &
        P3=$!

        python backend/manage.py runbot &
        P4=$!
        
        # Setup trap to kill background processes on exit
        trap 'echo -e "\n${RED}Stopping all services...${NC}"; kill $P1 $P2 $P3 $P4 2>/dev/null; exit' INT TERM EXIT
        
        wait
        ;;
    migrate)
        ensure_venv
        python backend/manage.py migrate --noinput
        echo -e "${GREEN}Migrations applied.${NC}"
        ;;
    seed)
        ensure_venv
        python backend/manage.py seed_demo
        echo -e "${GREEN}Demo data seeded.${NC}"
        ;;
    test)
        ensure_venv
        python -m pytest -v
        ;;
    shell)
        ensure_venv
        python backend/manage.py shell
        ;;
    db)
        psql -U yunoai -d yunoai
        ;;
    redis)
        redis-cli
        ;;
    logs)
        docker compose logs -f
        ;;
    help|--help|-h)
        usage
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        usage
        exit 1
        ;;
esac
