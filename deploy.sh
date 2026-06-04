#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[1;36m'
NC='\033[0m'

ENV_FILE="${1:-.env}"

echo -e "${CYAN}=== YunoAI Deploy ===${NC}"
echo ""

# ----------------------------------------------------------
# Validate .env
# ----------------------------------------------------------
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}ERROR: $ENV_FILE not found${NC}"
    echo "  Copy .env.example to .env and add your API keys."
    exit 1
fi

source "$ENV_FILE"

if [ -z "${DJANGO_SECRET_KEY:-}" ] || [ "$DJANGO_SECRET_KEY" = "change-me-to-a-long-random-string" ]; then
    echo -e "${RED}WARNING: DJANGO_SECRET_KEY is not set or still the default.${NC}"
    echo "  Generate one: python3 -c 'import secrets; print(secrets.token_urlsafe(50))'"
fi

# ----------------------------------------------------------
# Docker Compose Deploy
# ----------------------------------------------------------
echo -e "${CYAN}[1/4] Building and starting Docker services...${NC}"
docker compose build
docker compose up -d
echo -e "${GREEN}  Services started${NC}"

# ----------------------------------------------------------
# Wait for healthy
# ----------------------------------------------------------
echo -e "${CYAN}[2/4] Waiting for backend to be healthy...${NC}"
for i in $(seq 1 30); do
    if curl -s http://localhost:8000/api/workflows/ > /dev/null 2>&1; then
        echo -e "${GREEN}  Backend is ready${NC}"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo -e "${RED}  Backend did not become ready — check logs: docker compose logs backend${NC}"
        exit 1
    fi
    sleep 2
done

# ----------------------------------------------------------
# Migrate + Seed
# ----------------------------------------------------------
echo -e "${CYAN}[3/4] Running migrations...${NC}"
docker compose exec -T backend python manage.py migrate --noinput
echo -e "${GREEN}  Migrations applied${NC}"

echo -e "${CYAN}[4/4] Seeding demo data...${NC}"
docker compose exec -T backend python manage.py seed_demo
echo -e "${GREEN}  Demo data seeded${NC}"

echo ""
echo -e "${GREEN}=== Deployment complete ===${NC}"
echo ""
echo "  Backend API:  http://localhost:8000"
echo "  Flower:       http://localhost:5555"
echo "  Frontend:     http://localhost:3000"
echo ""
echo "  To view logs:  docker compose logs -f"
echo "  To stop:       docker compose down"
echo ""
echo -e "${CYAN}Next:${NC} Open http://localhost:3000/templates and click 'Deploy Template'"
