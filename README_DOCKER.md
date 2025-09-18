# Dockerized Setup

## Prerequisites
- Docker and Docker Compose v2

## Quick start
```bash
docker compose up --build -d
```
- API: http://localhost:8000
- Redis: localhost:6379

## Environment variables
- REDIS_URL: redis://redis:6379/0 (set by compose)
- DOWNLOAD_FOLDER: /data/downloads (mounted volume persistency)
- CACHE_TTL_MINUTES: 60 (default cache TTL)
- API_KEYS: comma-separated list for X-API-Key auth (e.g., "prod_key1,prod_key2")
- SECRET_KEY: server secret

To pass secrets:
```bash
API_KEYS=prod_key1 SECRET_KEY=change_me docker compose up -d
```

## Volumes
- app-data: stores /data (downloads, cache)
- redis-data: Redis persistence

## Services
- api: FastAPI (uvicorn)
- worker: Celery worker (uses Redis broker/backend)
- redis: Redis 7 server

## Logs
- Use `docker compose logs -f api` and `docker compose logs -f worker`

## Scaling workers
```bash
docker compose up --scale worker=3 -d
```

## Notes
- Ensure ffmpeg is available (preinstalled in Dockerfile).
- Use API key for /api/download endpoints.