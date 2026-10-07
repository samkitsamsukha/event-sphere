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

Implemented:
- User registration and login at `/api/auth/register` and `/api/auth/login`
- Argon2 password hashing and JWT bearer access tokens
- Authenticated user endpoint at `/api/auth/me`
- Customer and publisher role dependencies
- Profile retrieval and updates at `/api/users/me`
- Explicit interest relationships with add/list/remove endpoints at
  `/api/users/me/interests`
- Publisher event creation
- Publisher event update, publish, cancel, delete, and own-event listing
- Public published-event listing and detail discovery with keyword, category,
  location, date, pagination, and sorting filters
- Deterministic event semantic text generation and reusable lazy-loaded embeddings
- Behavioral interaction tracking at `/api/interactions`
- Configurable, explainable recommendations at `/api/recommendations`
- SQLAlchemy async database access
- Alembic migrations
- pgvector column
- Sentence-transformer embedding service

The current migration head is `0004_interactions`. Apply all migrations with:

```bash
alembic upgrade head
```

Recommendations use explicit interests, weighted behavioral history, time decay,
semantic embeddings, vector candidate generation, popularity, and recency. The
debug endpoint is development-only.

Interaction types are `VIEW`, `CLICK`, `SEARCH`, `LIKE`, `SAVE`, and `REGISTER`.
Short-window duplicate `VIEW`, `CLICK`, and `SEARCH` events are rejected.

Recommendation pipeline:

```text
event -> semantic text -> 384d embedding
     -> pgvector candidate generation
     -> eligibility filtering
     -> interest/behavior/recency/popularity features
     -> transparent weighted ranking
     -> recommendations
```

## Frontend integration

From `frontend`, configure:

```text
VITE_API_URL=http://127.0.0.1:8000/api
```

The React app stores the access token in local storage under
`eventsphere_access_token`, attaches it through the centralized Axios client,
and clears it after a `401 Unauthorized` response. Start both applications:

```powershell
# backend
uvicorn app.main:app --reload

# frontend
npm run dev
```

The frontend communicates with the backend through `frontend/src/api.js`.
