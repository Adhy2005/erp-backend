"""
app/middleware/auth.py
----------------------
JWT authentication middleware.
- create_access_token(): signs a JWT containing user email, role, user_id
- get_current_user(): reads + validates JWT from every request header
  Returns 401 if missing or expired.
- get_current_user_db(): DB-backed dependency — queries User by user_id from
  token. Raises 401 if user not found, 403 if inactive.
"""

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.db.session import get_db

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE_THIS_SECRET_KEY_IN_PRODUCTION")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")


def create_access_token(data: dict) -> str:
    """Creates a signed JWT token. Called at login."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    FastAPI dependency — reads JWT from Authorization: Bearer <token> header.
    Returns: {"sub": email, "role": role, "user_id": uuid_string}
    Raises 401 if invalid or expired.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        role: str = payload.get("role")
        user_id: str = payload.get("user_id")
        if email is None or role is None:
            raise credentials_exception
        return {"sub": email, "role": role, "user_id": user_id}
    except JWTError:
        raise credentials_exception


# ── Step 4: DB-backed current user dependency ─────────────────────────────────

def get_current_user_db(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """
    DB-backed JWT dependency.
    - Decodes token and extracts user_id
    - Queries User from DB by user_id
    - Raises HTTP 401 if user not found
    - Raises HTTP 403 if user.is_active is False
    Returns the SQLAlchemy User ORM object.
    """
    from app.models.users import User  # local import to avoid circular deps

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )
    return user
