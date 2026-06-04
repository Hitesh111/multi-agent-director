#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_DIR"

echo "=== YunoAI Setup ==="

# ----------------------------------------------------------
# 1. Check prerequisites
# ----------------------------------------------------------
echo "[1/7] Checking prerequisites..."

command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 not found"; exit 1; }
command -v node >/dev/null 2>&1   || { echo "ERROR: node not found"; exit 1; }
command -v psql >/dev/null 2>&1   || echo "  WARNING: psql not found — skip automatic DB creation"

PYTHON=$(python3 --version 2>&1 | grep -oP '\d+\.\d+')
echo "  python3: $(python3 --version)"
echo "  node:    $(node --version)"
echo "  npm:     $(npm --version)"

# ----------------------------------------------------------
# 2. Create .env if missing
# ----------------------------------------------------------
echo "[2/7] Environment file..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "  Created .env from .env.example — edit it with your API keys"
else
    echo "  .env already exists"
fi

# ----------------------------------------------------------
# 3. Backend virtual env + dependencies
# ----------------------------------------------------------
echo "[3/7] Backend Python virtual environment..."
if [ ! -d .venv ]; then
    python3 -m venv .venv
    echo "  Created .venv"
fi
source .venv/bin/activate
pip install --quiet -r backend/requirements/dev.txt
echo "  Python dependencies installed"

# ----------------------------------------------------------
# 4. Database setup
# ----------------------------------------------------------
echo "[4/7] Database..."
DB_EXISTS=$(psql -U yunoai -tAc "SELECT 1 FROM pg_database WHERE datname='yunoai'" 2>/dev/null || true)
if [ "$DB_EXISTS" != "1" ]; then
    createdb yunoai 2>/dev/null && echo "  Created database 'yunoai'" || echo "  WARNING: could not create database 'yunoai' — create it manually"
else
    echo "  Database 'yunoai' already exists"
fi

python backend/manage.py migrate --noinput
echo "  Migrations applied"

# ----------------------------------------------------------
# 5. Seed demo data
# ----------------------------------------------------------
echo "[5/7] Demo data..."
python backend/manage.py seed_demo
echo "  Demo agents and workflow seeded"

# ----------------------------------------------------------
# 6. Frontend dependencies
# ----------------------------------------------------------
echo "[6/7] Frontend..."
cd frontend
npm install --silent
cd "$APP_DIR"
echo "  Frontend dependencies installed"

# ----------------------------------------------------------
# 7. Create superuser (optional)
# ----------------------------------------------------------
echo "[7/7] Superuser..."
python backend/manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('  Created superuser: admin / admin123')
else:
    print('  Superuser already exists')
" 2>/dev/null || echo "  (skipped)"

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit .env — add DEEPSEEK_API_KEY and/or OPENCODE_API_KEY"
echo "  2. Start the backend:  source .venv/bin/activate && python backend/manage.py runserver 0.0.0.0:8000"
echo "  3. Start Celery:       source .venv/bin/activate && celery -A config.celery worker -l info"
echo "  4. Start frontend:     cd frontend && npm run dev"
echo "  5. Open http://localhost:3000"
