#!/usr/bin/env bash
# Boot the whole app in one container: Django (ASGI) + Next.js behind nginx.
set -e

export PORT="${PORT:-10000}"

# --- Django: prepare and start on internal :8000 --------------------------
cd /app/backend
python manage.py collectstatic --noinput
python manage.py migrate --noinput
daphne -b 127.0.0.1 -p 8000 config.asgi:application &

# --- Next.js: start on internal :3000 -------------------------------------
cd /app/frontend
node node_modules/next/dist/bin/next start -H 127.0.0.1 -p 3000 &

# --- nginx: public entrypoint on $PORT ------------------------------------
envsubst '${PORT}' < /app/deploy/nginx.conf.template > /etc/nginx/nginx.conf
exec nginx -g 'daemon off;'
