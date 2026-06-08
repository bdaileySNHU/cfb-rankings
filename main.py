"""Gunicorn / uvicorn entry-point shim.

The application is defined in ``src/api/main.py``. This module re-exports it so
that ``gunicorn -c gunicorn_config.py main:app`` (see deploy/cfb-rankings.service)
resolves from the project root without relying on an untracked shim on the
server. Run locally with ``uvicorn main:app --reload``.
"""

from src.api.main import app  # noqa: F401

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
