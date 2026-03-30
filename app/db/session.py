"""
app/db/session.py
-----------------
Provides get_db() — the FastAPI dependency used by all routes to get a database session.
This uses the team's existing SessionLocal from database.py.
"""

from app.db.database import SessionLocal


def get_db():
    """
    Yields a database session for each request, then closes it automatically.
    Used in routes as: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
