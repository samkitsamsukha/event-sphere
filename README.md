# EventSphere

EventSphere is a personalized event discovery application with a React
frontend, a FastAPI backend, and PostgreSQL with the `pgvector` extension.
The root Docker Compose file runs the complete application stack.

## Quick start with Docker

### Prerequisites

Install and start:

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) on
  Windows or macOS, or Docker Engine with the Compose plugin on Linux
- Git, if you are cloning the repository

Docker Desktop must be running before you execute the commands below. The
application uses Docker Compose v2, so the command is `docker compose` (with a
space), not the legacy `docker-compose` command.

### 1. Get the source code

```powershell
git clone https://github.com/samkitsamsukha/event-sphere.git
Set-Location event-sphere
```

If you already have the project, open a terminal in the repository root
(the directory containing `docker-compose.yml`).

### 2. Create the Docker environment file

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

macOS/Linux:

```bash
cp .env.example .env
```

Open `.env` and replace both placeholder values:

```dotenv
POSTGRES_PASSWORD=use-a-local-database-password
JWT_SECRET_KEY=use-at-least-32-random-characters
```

Do not commit `.env`. It contains credentials and is intended for local
configuration. The example file is safe to commit.

For a local Docker run, the remaining values can stay as follows:

```dotenv
POSTGRES_USER=eventsphere
POSTGRES_DB=eventsphere
CORS_ORIGINS=http://localhost
VITE_API_URL=http://localhost:8000/api
```

`JWT_SECRET_KEY` must contain at least 32 characters. `CORS_ORIGINS` is a
comma-separated allowlist; wildcard origins such as `*` are not accepted.

### 3. Build and start all services

From the repository root:

```powershell
docker compose up --build -d
```

The first build may take several minutes because the backend installs the
Python dependencies and the frontend installs Node dependencies. Compose
starts:

| Service | Purpose | Local address |
| --- | --- | --- |
| `db` | PostgreSQL 16 with pgvector | Internal only |
| `backend` | FastAPI API and Alembic migrations | http://localhost:8000 |
| `frontend` | Production React build served by Nginx | http://localhost |

The backend waits for the database health check, runs
`alembic upgrade head`, and then starts Uvicorn. No separate migration command
is required for a normal Docker startup.

The admin role is added by migration `0006_admin_role`. Existing databases are
upgraded automatically on the next backend start.

### 4. Confirm that the stack is running

```powershell
docker compose ps
docker compose logs -f backend
```

In another terminal, check the services:

```powershell
Invoke-WebRequest http://localhost/ -UseBasicParsing
Invoke-WebRequest http://localhost:8000/health -UseBasicParsing
Invoke-WebRequest http://localhost:8000/health/db -UseBasicParsing
```

The two API health endpoints should return HTTP 200 with:

```json
{"status":"ok"}
```

Open the application in a browser:

- Frontend: http://localhost
- Swagger API documentation: http://localhost:8000/docs
- API health: http://localhost:8000/health

Register an account from the frontend to begin exploring events. Publisher
features are available to accounts with the publisher role.

### 5. Load demo accounts and event data

After the backend container is healthy, run the repeatable seed script:

```powershell
docker compose exec backend python scripts/seed_demo.py
```

This creates six published events and these local-only demo accounts:

| Account | Email | Password | Use |
| --- | --- | --- | --- |
| Admin | `admin@eventsphere.example.com` | `Admin12345!` | Open `/admin` to create, publish, cancel, and delete events |
| Explorer | `demo@eventsphere.example.com` | `Demo12345!` | Test customer discovery, recommendations, saves, and registration |
| Publisher | `publisher@eventsphere.example.com` | `Publisher12345!` | Test the publisher event studio |

These are intentionally predictable demo credentials. Never use them in a
shared, public, or production environment. The seed command is idempotent and
can be run again to restore the demo events.

Sign in at http://localhost/login. The admin panel is at
http://localhost/admin and is visible in the navigation only for the admin
account. Public event pages are available from Explore and use routes such as
`/events/1` after the seed data has loaded.

## Common Docker commands

Run these commands from the repository root:

```powershell
# Follow all service logs
docker compose logs -f

# Follow only backend logs
docker compose logs -f backend

# Show service status
docker compose ps

# Stop containers but keep the database volume
docker compose down

# Start existing containers again
docker compose up -d

# Rebuild images after changing source or dependencies
docker compose up --build -d
```

To stop the stack and permanently delete the local PostgreSQL data:

```powershell
docker compose down -v
```

The `-v` option is destructive: it removes the `postgres_data` volume,
including users, events, and all other database records. Use it only when you
want a completely clean local database.

## Configuration

The root `.env` file is read by Docker Compose. The root
[`docker-compose.yml`](./docker-compose.yml) uses these variables:

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `POSTGRES_USER` | No | `eventsphere` | Database username |
| `POSTGRES_PASSWORD` | Yes | None | Database password |
| `POSTGRES_DB` | No | `eventsphere` | Database name |
| `JWT_SECRET_KEY` | Yes | None | Secret used to sign access tokens; minimum 32 characters |
| `CORS_ORIGINS` | No | `http://localhost` | Allowed browser origins, comma-separated |
| `VITE_API_URL` | No | `http://localhost:8000/api` | API URL compiled into the frontend image |

`VITE_API_URL` is a build-time frontend setting. If it changes, rebuild the
frontend image:

```powershell
docker compose build frontend
docker compose up -d frontend
```

For a different host or reverse proxy, set `VITE_API_URL` to the URL that the
browser can reach and set `CORS_ORIGINS` to the frontend origin. Do not use
Docker's internal hostname `backend` as `VITE_API_URL`; the browser runs
outside the Compose network.

## How the Docker stack works

The root Compose file defines three services:

1. `db` uses `pgvector/pgvector:pg16` and stores data in the named
   `postgres_data` volume.
2. `backend` is built from [`backend/Dockerfile`](./backend/Dockerfile).
   It connects to `db` using the internal Compose hostname, applies all
   Alembic migrations, and serves FastAPI on port 8000.
3. `frontend` is built from [`frontend/Dockerfile`](./frontend/Dockerfile).
   Vite creates a production bundle and Nginx serves it on port 80 with SPA
   fallback routing.

The database is intentionally not published to the host by the root Compose
file. The backend reaches it at `db:5432` inside the Compose network.

## Troubleshooting

### `POSTGRES_PASSWORD` or `JWT_SECRET_KEY` is missing

Create `.env` from `.env.example`, then set both required values:

```powershell
Copy-Item .env.example .env -Force
notepad .env
docker compose up --build -d
```

### The backend is unhealthy or exits during startup

Inspect the database and backend logs:

```powershell
docker compose logs db
docker compose logs backend
```

The backend depends on the database health check and will not start until
PostgreSQL accepts connections. If the database volume contains an invalid
local setup and you do not need its data, recreate it:

```powershell
docker compose down -v
docker compose up --build -d
```

### Port 80 or 8000 is already in use

Stop the process using the port, or change the host side of the mapping in
`docker-compose.yml`. For example, `"8080:80"` makes the frontend available at
http://localhost:8080. If the frontend host port changes, update
`CORS_ORIGINS` in `.env` and rebuild the frontend:

```dotenv
CORS_ORIGINS=http://localhost:8080
```

### The frontend loads but API calls fail

Check that the API is reachable at http://localhost:8000/health and that
`.env` contains:

```dotenv
VITE_API_URL=http://localhost:8000/api
CORS_ORIGINS=http://localhost
```

Because `VITE_API_URL` is compiled into the frontend image, run
`docker compose up --build -d` after changing it.

### Changes are not visible

Rebuild the affected image and recreate its container:

```powershell
docker compose up --build -d backend frontend
```

If dependency installation is cached unexpectedly, use:

```powershell
docker compose build --no-cache backend frontend
docker compose up -d
```

## Local development without the full application container

Docker Compose is the recommended getting-started path. If you want frontend
hot reload or backend reload, run only the database:

```powershell
docker compose up -d db
```

Then configure the backend and frontend separately using their own example
files:

- Backend: [`backend/README.md`](./backend/README.md)
- Frontend: [`frontend/README.md`](./frontend/README.md)

The locally running backend must use a database URL pointing to
`localhost:5432`, and the locally running frontend should use:

```dotenv
VITE_API_URL=http://127.0.0.1:8000/api
```

The root Compose file does not publish PostgreSQL's port. If you use this
hybrid development mode, add a temporary `5432:5432` port mapping to the
`db` service or use the dedicated
[`backend/docker-compose.yml`](./backend/docker-compose.yml), which publishes
PostgreSQL on port 5432 with its documented local credentials.

## Tests and checks

After the Docker stack is running, run the existing checks from the relevant
directories:

```powershell
# Backend
Set-Location backend
python -m pytest -q
python -m ruff check app tests

# Frontend
Set-Location ..\frontend
npm test
npm run lint
npm run build
```

These commands use local Python and Node installations. They are not required
to run the Docker application.

## Project layout

```text
backend/       FastAPI API, SQLAlchemy models, services, and Alembic migrations
frontend/      React/Vite application and Nginx production image
docker-compose.yml
.env.example
```

## Production notes

The root Compose setup is suitable for local development and demonstrations.
For production, use deployment-specific secrets, a managed PostgreSQL/pgvector
service where appropriate, HTTPS at a reverse proxy, restricted CORS origins,
and a high-entropy JWT secret supplied by a secret manager. Do not expose the
database publicly or use the placeholder values from `.env.example`.
