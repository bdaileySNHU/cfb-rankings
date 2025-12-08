"""Database Configuration and Session Management

This module configures SQLAlchemy database connections and provides
session management utilities for the ranking system.

Configuration:
    - Uses SQLite by default (cfb_rankings.db)
    - Supports PostgreSQL via DATABASE_URL environment variable
    - Thread-safe session management with proper cleanup

Functions:
    - init_db: Create all database tables from ORM models
    - get_db: FastAPI dependency for database sessions
    - reset_db: Drop and recreate all tables (destructive)

Example:
    Initialize database:
        >>> from database import init_db
        >>> init_db()
        Database initialized successfully!

    Use with FastAPI dependency injection:
        >>> @app.get("/teams")
        >>> def get_teams(db: Session = Depends(get_db)):
        ...     return db.query(Team).all()

Note:
    The get_db() dependency automatically handles session cleanup,
    ensuring connections are properly closed even if exceptions occur.
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.models.models import Base

# SQLite database for development
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./cfb_rankings.db")

# Create engine
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database by creating all tables from ORM models.

    Creates all tables defined in models.py using SQLAlchemy's metadata.
    Safe to run multiple times - only creates missing tables, doesn't
    modify existing ones.

    This should be called on first application startup or when new models
    are added. For schema changes, use Alembic migrations instead.

    Example:
        >>> from database import init_db
        >>> init_db()
        Database initialized successfully!
    """
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully!")


def get_db():
    """FastAPI dependency for database session management.

    Yields a database session that is automatically closed after use,
    even if an exception occurs. Use with FastAPI's Depends() for
    automatic dependency injection.

    Yields:
        Session: SQLAlchemy database session

    Example:
        >>> from fastapi import Depends
        >>> from database import get_db
        >>>
        >>> @app.get("/teams")
        >>> def get_teams(db: Session = Depends(get_db)):
        ...     return db.query(Team).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def reset_db():
    """Drop all tables and recreate from ORM models.

    **WARNING: This is destructive!** All data will be permanently lost.
    Only use for development/testing or when you need to completely
    reset the database schema.

    For production schema changes, use Alembic migrations instead.

    Example:
        >>> from database import reset_db
        >>> reset_db()
        Database reset successfully!
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("Database reset successfully!")


if __name__ == "__main__":
    print("Initializing database...")
    init_db()
