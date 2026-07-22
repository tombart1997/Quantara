#!/usr/bin/env bash
# Build the distribution bundle: quantara-dist.zip
# Run from the repo root:  bash scripts/package.sh
set -euo pipefail
cd "$(dirname "$0")/.."

BUNDLE=dist-package/quantara
echo "==> Building frontend..."
cd frontend
# npm install (not ci): ci wipes node_modules, which fails while the dev
# server has files locked.
npm install --silent
npm run build --silent
cd ..

echo "==> Assembling bundle..."
rm -rf dist-package
mkdir -p "$BUNDLE"

# Backend (no venv, no data, no caches)
mkdir -p "$BUNDLE/backend"
cp -r backend/app backend/alembic backend/alembic.ini backend/requirements.txt "$BUNDLE/backend/"
find "$BUNDLE/backend" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Prebuilt frontend (served by the backend — recipient needs no Node)
cp -r frontend/dist/frontend/browser "$BUNDLE/frontend_dist"

# Recipient scripts + config
cp scripts/dist/setup.sh scripts/dist/setup.bat scripts/dist/run.sh scripts/dist/run.bat scripts/dist/README.txt "$BUNDLE/"
cp .env.example "$BUNDLE/.env"

echo "==> Creating zip..."
cd dist-package
zip -qr quantara-dist.zip quantara
cd ..
echo "DONE: dist-package/quantara-dist.zip"
du -h dist-package/quantara-dist.zip
