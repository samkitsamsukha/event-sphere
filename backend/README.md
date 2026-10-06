# EventSphere Backend

FastAPI + PostgreSQL + pgvector + SQLAlchemy + Alembic backend starter for the EventSphere personalized event discovery platform.

## 1. Start PostgreSQL + pgvector

```bash
docker compose up -d db
```

## 2. Create virtual environment

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

## 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 4. Configure environment

```bash
copy .env.example .env
```

On macOS/Linux use `cp .env.example .env`.

Generate a strong JWT secret and replace `JWT_SECRET_KEY` in `.env`.

## 5. Enable pgvector and create schema

```bash
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

The initial migration should include the `vector` extension and embedding column. If your generated migration does not include the extension, add `op.execute("CREATE EXTENSION IF NOT EXISTS vector")` before creating vector columns.

## 6. Run API

```bash
uvicorn app.main:app --reload
```

Open:
- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/docs

## Current scope

Implemented starter pieces:
- User registration/login
- Argon2 password hashing
- JWT access tokens
- Role field for CUSTOMER/PUBLISHER
- Current-user endpoint
- Publisher event creation
- Public event listing/detail
- SQLAlchemy async database access
- Alembic migrations
- pgvector column
- Sentence-transformer embedding service

Next modules should add registrations, interests, interactions, recommendation retrieval/ranking, and background embedding updates.
