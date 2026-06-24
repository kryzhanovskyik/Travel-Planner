# Travel Planner API

A RESTful API for managing travel projects and places built with FastAPI, SQLite, and Redis.

## Features

- Travel project CRUD (create with places in one request, update, delete, list)
- Places sourced from the [Art Institute of Chicago API](https://api.artic.edu/docs/#collections) with validation and 24h caching
- Notes per place (add, update)
- Mark a place as visited — project auto-completes when all places are visited
- JWT Bearer authentication with token revocation (logout)
- Pagination and filtering on list endpoints
- Docker + Docker Compose setup

## Tech Stack

- **FastAPI** — web framework
- **SQLAlchemy (async)** + **aiosqlite** — ORM and SQLite database
- **Redis** — caching Art Institute API responses
- **PyJWT** + **bcrypt** — authentication
- **Poetry** — dependency management

## Quick Start (Docker)

```bash
git clone <repo-url>
cd travel_planner
docker compose up --build
```

The API will be available at `http://localhost:8001`.

Interactive docs (Swagger UI): `http://localhost:8001/docs`

## Local Setup (without Docker)

**Requirements:** Python 3.12+, Poetry, Redis

1. Install dependencies:

```bash
poetry install
```

2. Copy and configure environment variables:

```bash
cp .env.example .env
```

3. Start Redis (if not already running):

```bash
redis-server
```

4. Run the application:

```bash
poetry run uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./travel_planner.db` | SQLAlchemy database URL |
| `SECRET_KEY` | `SUPER_SECRET_KEY` | JWT signing secret — **change in production** |
| `ACCESS_TOKEN_EXPIRE_DAYS` | `30` | JWT lifetime in days |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |

## API Overview

### Auth

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/register` | Register a new user |
| `POST` | `/auth/login` | Log in, receive a Bearer token |
| `GET` | `/auth/me` | Get current user info |
| `POST` | `/auth/logout` | Revoke current token |

### Projects

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/projects` | Create a project (optionally with places) |
| `GET` | `/projects` | List projects (pagination + `is_completed` filter) |
| `GET` | `/projects/{id}` | Get a single project |
| `PATCH` | `/projects/{id}` | Update project name / description / start date |
| `DELETE` | `/projects/{id}` | Delete a project (blocked if any place is visited) |

### Places

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/projects/{id}/places` | Add a place (validated against Chicago API) |
| `GET` | `/projects/{id}/places` | List places (pagination + `is_visited` filter) |
| `GET` | `/projects/{id}/places/{pid}` | Get a single place |
| `PATCH` | `/projects/{id}/places/{pid}` | Update place title |
| `PATCH` | `/projects/{id}/places/{pid}/visit` | Mark place as visited |

### Notes

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/projects/{id}/places/{pid}/notes` | Add a note to a place |
| `GET` | `/projects/{id}/places/{pid}/notes/{nid}` | Get a single note |
| `PATCH` | `/projects/{id}/places/{pid}/notes/{nid}` | Update a note |
| `DELETE` | `/projects/{id}/places/{pid}/notes/{nid}` | Delete a note |

## Business Rules

- A project can hold **1–10 places**
- The same artwork (external ID) cannot be added to the same project twice
- A project **cannot be deleted** if any of its places are already marked as visited
- When **all places** in a project are marked as visited, the project is automatically marked as completed

## API Documentation

Full Swagger UI is available at `/docs` once the application is running.

A Postman collection is included in the repository: `Travel Planner.postman_collection.json`
