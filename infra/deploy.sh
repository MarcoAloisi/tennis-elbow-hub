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

echo "Checking media storage config..."
if ! grep -q '^MEDIA_ROOT=' .env 2>/dev/null || ! grep -q '^MEDIA_BASE_URL=' .env 2>/dev/null; then
    echo "ERROR: MEDIA_ROOT and MEDIA_BASE_URL must be set in backend/.env" >&2
    exit 1
fi
MEDIA_ROOT=$(grep '^MEDIA_ROOT=' .env | cut -d= -f2-)
sudo mkdir -p "$MEDIA_ROOT"/{outfits,guide-thumbnails,guide-images,avatars}
sudo chown -R www-data:www-data "$MEDIA_ROOT"

echo "Running migrations..."
.venv/bin/alembic upgrade head

echo "Restarting backend..."
sudo systemctl restart te4-backend

echo "Reloading nginx..."
sudo nginx -t && sudo systemctl reload nginx

echo "Done. Check status:"
sudo systemctl status te4-backend --no-pager
