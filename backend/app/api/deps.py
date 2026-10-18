from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User, get_user_by_id

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    """Add this to any route that only logged-in users may reach."""
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Please log in to continue",
                            headers={"WWW-Authenticate": "Bearer"})
    user_id = decode_access_token(creds.credentials)
    user = get_user_by_id(db, user_id) if user_id is not None else None
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Your session has expired. Please log in again",
                            headers={"WWW-Authenticate": "Bearer"})
    return user