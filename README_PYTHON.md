# Scientific Discovery (Python Modular Backend)

This is a secure, modular Python backend for the journal indexer using SQLite.

## Stack
- FastAPI
- SQLAlchemy
- SQLite (`data/journal_indexer.db`)
- JWT auth (administrator / curator)

## Run
1. Create virtual environment:
   - `python3 -m venv .venv`
   - `source .venv/bin/activate`
2. Install deps:
   - `pip install -r requirements.txt`
3. Start API:
   - `uvicorn app.main:app --reload --port 8000`
4. Open docs:
   - `http://127.0.0.1:8000/docs`

## Default Admin
- username: `admin`
- password: `admin123`

Change credentials in `.env`:
- `DEFAULT_ADMIN_USERNAME`
- `DEFAULT_ADMIN_PASSWORD`
- `SECRET_KEY`

## Main Endpoints
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/users` (admin only)
- `GET/POST /api/v1/endpoints`
- `POST /api/v1/endpoints/batch`
- `POST /api/v1/endpoints/{id}/sync`
- `POST /api/v1/endpoints/{id}/harvest`
- `DELETE /api/v1/endpoints/{id}`
- `GET /api/v1/journals`
- `PUT /api/v1/journals/{endpoint_id}`
- `GET /api/v1/articles?q=...&endpoint_id=...`

## Notes
- Persistent storage is now SQLite file in repo: `data/journal_indexer.db`.
- Existing `index.html` can be migrated step-by-step to call this API.
