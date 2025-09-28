# Chat Service (FastAPI, PostgreSQL, Redis)

A minimal 1:1 chat microservice demonstrating auth, messaging, Redis caching, and containerization. Built with FastAPI and Poetry.

## Features
- User registration and login (JWT Bearer)
- Send messages and fetch conversation history (newest-first, paginated)
- Redis caching for recent conversation window
- Fixed-window rate limits: login (5/min per IP), send (30/min per user)
- Plain-text logging with request IDs
- Health endpoint `/health`

## API
- POST `/register`: { username, email, password } -> 201 UserPublic
- POST `/login`: { username, password } -> 200 { access_token, token_type, expires_in }
- POST `/send` (auth): { recipient_id, content }
- GET `/messages` (auth): params: peer_id, limit=5, offset=0

## Configuration
Environment variables (example values shown):
- `SECRET_KEY=please-change`
- `ACCESS_TOKEN_EXP_MINUTES=60`
- `RATE_LIMIT_LOGIN_PER_MIN=5`
- `RATE_LIMIT_SEND_PER_MIN=30`
- `DB_USER=postgres`
- `DB_PASSWORD=postgres`
- `DB_HOST=localhost`
- `DB_PORT=5432`
- `DB_NAME=chat_service`
- `REDIS_URL=redis://localhost:6379/0`
  
Optional:
- `DATABASE_URL_ENV` (overrides full DB URL; tests use `sqlite+aiosqlite:///:memory:`)

You can place these in a `.env` file (not committed).

## Local Run

Create and activate a Python 3.11 virtual environment:

- Linux/macOS (bash/zsh):
```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

- Windows (PowerShell):
```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
```

- Windows (CMD):
```bat
py -3.11 -m venv .venv
.venv\Scripts\activate.bat
```

Using Poetry:
```bash
poetry install
poetry run uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000
```
OpenAPI docs: http://localhost:8000/docs

Database tables are created on startup via lifespan (no migrations in this PoC).

## Docker
A simple Dockerfile is provided. Build and run with external Postgres and Redis:
```bash
docker build -t chat-service .
# Provide env vars pointing to your DB/Redis
docker run --rm -p 8000:8000 \
  -e SECRET_KEY=please-change \
  -e DB_HOST=host.docker.internal -e DB_USER=postgres -e DB_PASSWORD=postgres -e DB_NAME=chat_service \
  -e REDIS_URL=redis://host.docker.internal:6379/0 \
  chat-service
```

## Linting / Formatting / Types
```bash
poetry run black .
poetry run mypy app
```

## Testing
- The test suite uses an in-memory SQLite database and a fake Redis.
- No extra services are required to run tests.

Run tests:
```bash
poetry run pytest -q
```

Notes:
- Tests set `DATABASE_URL_ENV=sqlite+aiosqlite:///:memory:` automatically.
- For manual testing with Postgres/Redis, copy `.env.example` to `.env`, set values, then run the server.

## Minimal Tests (smoke)
```bash
poetry run pytest -q
```

## Notes / Assumptions
- Proof-of-concept scale, single-tenant, 1:1 messaging only.
- Sender is derived from JWT; no edit/delete/read-receipts.
- Caching prioritizes performance with short TTL and windowed list.
- Future work (Plus): monitoring stack, comprehensive tests.

