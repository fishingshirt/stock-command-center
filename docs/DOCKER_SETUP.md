# Docker Setup Specification

## Goal
Running `docker compose up` in the repo root should spin up a fully working dashboard on `http://localhost:8080`.

## Docker Compose (`docker/docker-compose.yml`)
```yaml
version: "3.9"

services:
  backend:
    build:
      context: ..
      dockerfile: docker/Dockerfile.backend
    container_name: scc-backend
    ports:
      - "8000:8000"
    volumes:
      - ../dashboard/data:/app/data
      - ../logs:/app/logs
      - ../whiteboard:/app/whiteboard
    environment:
      - DATA_DIR=/app/data
      - WHITEBOARD_PATH=/app/whiteboard/kanban.md
    networks:
      - scc-net

  frontend:
    build:
      context: ..
      dockerfile: docker/Dockerfile.frontend
    container_name: scc-frontend
    ports:
      - "8080:80"
    depends_on:
      - backend
    networks:
      - scc-net

networks:
  scc-net:
    driver: bridge
```

## Backend Dockerfile (`docker/Dockerfile.backend`)
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# System deps
RUN apt-get update \&\& apt-get install -y --no-install-recommends git \&\& rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY dashboard/backend ./backend
COPY whiteboard /app/whiteboard
COPY bots ./bots
COPY docs ./docs

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Frontend Dockerfile (`docker/Dockerfile.frontend`)
```dockerfile
FROM node:20-alpine AS builder

WORKDIR /app
COPY dashboard/frontend/package*.json ./
RUN npm ci

COPY dashboard/frontend ./
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

## Nginx Config (`docker/nginx.conf`)
```nginx
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://scc-backend:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Directory Structure After Docker Wiring
```
stock-command-center/
├── docker/
│   ├── docker-compose.yml   # move orchestration up later if desired
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── nginx.conf
├── dashboard/
│   ├── backend/               # FastAPI app
│   │   ├── main.py
│   │   └── routers/
│   ├── frontend/              # React + Vite
│   │   ├── src/
│   │   ├── public/
│   │   ├── index.html
│   │   ├── vite.config.js
│   │   └── package.json
│   └── data/                  # SQLite or JSON output
│       └── output/
├── bots/
├── whiteboard/
├── docs/
├── requirements.txt
└── README.md
```

## Local Development (no Docker)
```bash
# Backend
cd dashboard/backend
pip install -r ../../requirements.txt
uvicorn main:app --reload --port 8000

# Frontend (new terminal)
cd dashboard/frontend
npm install
npm run dev
# open http://localhost:5173
```

## Production Consideration
- Mount `dashboard/data/` and `whiteboard/` as volumes so data persists across container restarts.
- If using SQLite, store the DB file inside `dashboard/data/` (bind-mounted).
- Cron job for bots should run **outside** Docker for this MVP (or use a separate `cron` container if desired later).

## For the Next AI
When you implement Docker:
1. Place all Docker files exactly as spec'd above.
2. Make sure `docker compose up` works end-to-end with mocked data before wiring real APIs.
3. The dashboard should show the sample cards immediately on first build.
