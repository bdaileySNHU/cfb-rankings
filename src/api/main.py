"""College Football Ranking API - Main Application

This module constructs the FastAPI application for the Modified ELO ranking
system and wires together the per-domain route modules in ``src/api/routers``.

The system tracks team rankings using a Modified ELO algorithm that incorporates
recruiting rankings, transfer portal data, and returning production. It provides
comprehensive prediction capabilities and historical ranking tracking.

Route modules (see ``src/api/routers/``):
    - teams: CRUD operations for college football teams
    - games: Game management and automatic ranking updates
    - predictions: Generate predictions and track accuracy
    - rankings: Current rankings, postseason, and historical data
    - seasons: Season management and configuration
    - meta: Health check, system-wide statistics, ranking recalculation
    - admin: API usage monitoring, imports, config, and manual updates

Example:
    Run the application with uvicorn:
        $ uvicorn main:app --reload --host 0.0.0.0 --port 8000

    Access the interactive API documentation:
        http://localhost:8000/docs

    Check system health:
        $ curl http://localhost:8000/

Note:
    This application requires a configured database (SQLite by default)
    and optional CFBD API key for data imports.
"""

import logging

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables from .env file
load_dotenv()

from src.api.routers import (
    admin,
    games,
    meta,
    predictions,
    rankings,
    seasons,
    teams,
)
from src.models.database import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="College Football Ranking API",
    description="Modified ELO ranking system for college football with recruiting, transfers, and returning production",
    version="1.0.0",
)

from fastapi.staticfiles import StaticFiles

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount frontend static files
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")



# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize database on application startup.

    Creates all database tables if they don't exist using SQLAlchemy's
    create_all() method. This is safe to run multiple times as it only
    creates missing tables.

    Note:
        This runs automatically when FastAPI starts. For production
        deployments, consider using Alembic migrations instead.
    """
    init_db()


# Register route modules. Full route paths (e.g. "/api/rankings") are declared
# on each router's decorators, so URLs are unchanged from the monolithic layout.
app.include_router(meta.router)
app.include_router(teams.router)
app.include_router(games.router)
app.include_router(predictions.router)
app.include_router(rankings.router)
app.include_router(seasons.router)
app.include_router(admin.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
