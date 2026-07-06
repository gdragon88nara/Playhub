# Single-service deploy: one container serving the whole app on one URL.
# nginx fronts two internal processes — Next.js (UI) and Django/Channels
# (API + WebSockets) — so the frontend talks to the API same-origin (no CORS,
# no cross-service URL wiring). This is what Render runs.

# ---------- Stage 1: build the Next.js frontend ----------
FROM node:20-bookworm-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# Same-origin in production → API/media/ws calls are relative to the host.
ENV NEXT_PUBLIC_API_BASE=""
RUN npm run build

# ---------- Stage 2: runtime (Node + Python + nginx) ----------
FROM node:20-bookworm-slim
ENV PYTHONUNBUFFERED=1 NODE_ENV=production

RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 python3-venv python3-pip nginx gettext-base \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

# Python deps in an isolated venv.
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/ backend/

# Frontend build output + runtime (needed by `next start`).
COPY --from=frontend /app/frontend/.next frontend/.next
COPY --from=frontend /app/frontend/public frontend/public
COPY --from=frontend /app/frontend/node_modules frontend/node_modules
COPY --from=frontend /app/frontend/package.json frontend/package.json
COPY --from=frontend /app/frontend/next.config.ts frontend/next.config.ts

COPY deploy/ deploy/
RUN chmod +x deploy/start.sh

EXPOSE 10000
CMD ["bash", "deploy/start.sh"]
