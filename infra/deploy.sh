#!/bin/bash
# Run on VPS: ./deploy.sh
# Pulls latest code, runs migrations, restarts backend

set -e

cd /var/www/te4

echo "Pulling latest code..."
git fetch origin
git checkout ionos-migration
git pull origin ionos-migration

echo "Installing backend deps..."
cd backend
.venv/bin/pip install -r requirements.txt

echo "Running migrations..."
.venv/bin/alembic upgrade head

echo "Restarting backend..."
sudo systemctl restart te4-backend

echo "Done. Check status:"
sudo systemctl status te4-backend --no-pager
