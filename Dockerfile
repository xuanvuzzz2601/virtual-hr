# ── Stage 1: Build Next.js frontend ──────────────────────────────────────────
FROM node:20-alpine AS frontend-builder
WORKDIR /frontend

COPY frontend/package*.json ./
RUN npm ci --frozen-lockfile

COPY frontend/ .

# Empty base URL → frontend uses relative paths (/api/*), nginx proxies to FastAPI
ENV NEXT_PUBLIC_API_URL=""
RUN npm run build

# ── Stage 2: Final runtime image ─────────────────────────────────────────────
FROM python:3.10-slim

# Install Node.js 20, nginx, supervisor
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gnupg ca-certificates nginx supervisor \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Python backend ────────────────────────────────────────────────────────────
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/

# ── Next.js frontend (production build) ───────────────────────────────────────
COPY --from=frontend-builder /frontend/.next ./frontend/.next
COPY --from=frontend-builder /frontend/public ./frontend/public
COPY --from=frontend-builder /frontend/package*.json ./frontend/
COPY --from=frontend-builder /frontend/node_modules ./frontend/node_modules
COPY --from=frontend-builder /frontend/next.config.ts ./frontend/

# ── nginx & supervisor config ─────────────────────────────────────────────────
COPY nginx.conf /etc/nginx/nginx.conf
COPY supervisord.conf /etc/supervisord.conf

# Uploads directory for CV files + supervisor log dir
RUN mkdir -p /app/uploads /var/log/supervisor

# Copy backend .env (secrets injected at runtime via AgentBase env vars)
COPY backend/.env ./backend/.env

# Port 8080: required by AgentBase
EXPOSE 8080

CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisord.conf"]
