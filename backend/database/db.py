# backend/database/db.py

"""
DATABASE CONNECTION — SQLite setup using SQLAlchemy

WHY SQLALCHEMY?
SQLAlchemy is an ORM (Object Relational Mapper).
It lets you work with database tables as Python classes
instead of writing raw SQL strings everywhere.

WHY SQLITE?
SQLite = a simple file-based database.
Perfect for development and small projects.
No server to install — it's just a .db file.
Later you can swap it for PostgreSQL with minimal code change.

HOW SQLALCHEMY SESSIONS WORK:
  A "session" = one database transaction.
  You open a session → make changes → commit → close.
  
  We use FastAPI's dependency injection to give each
  HTTP request its own session, automatically closed when done.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from backend.config import DB_PATH

# Make sure the data directory exists
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# ── DATABASE ENGINE ───────────────────────────────────────────────────────────
# The "engine" is the connection to the database file
# connect_args={"check_same_thread": False} is required for SQLite
# with FastAPI because multiple threads may use the same connection
DATABASE_URL = f"sqlite:///{DB_PATH}"
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# ── SESSION FACTORY ───────────────────────────────────────────────────────────
# SessionLocal is a class that creates new database sessions
# autocommit=False → we manually commit transactions
# autoflush=False  → we manually flush changes
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ── BASE CLASS ────────────────────────────────────────────────────────────────
# All our database models inherit from this Base class
# SQLAlchemy uses it to know which classes are database tables
Base = declarative_base()


def get_db():
    """
    FastAPI dependency that provides a database session.
    
    Usage in a route:
        @app.get("/something")
        def my_route(db: Session = Depends(get_db)):
            ...
    
    The 'yield' makes this a generator function.
    Code BEFORE yield runs before the request.
    Code AFTER yield runs after the request (cleanup).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """
    Creates all database tables if they don't exist.
    Called once when the application starts.
    """
    from backend.database.models import Base as ModelBase
    ModelBase.metadata.create_all(bind=engine)
    print("✅ Database tables created/verified")