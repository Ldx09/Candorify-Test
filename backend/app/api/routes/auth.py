from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import create_user, get_user_by_email
from app.schemas.auth import LoginRequest, SignupRequest, SignupResponse, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])

EMAIL_TAKEN = "An account with this email already exists"


def _token_fields(user_id: int, remember_me: bool) -> dict:
    token, expires = create_access_token(user_id, remember_me)
    return {"access_token": token, "token_type": "bearer", "expires_at": expires,
            "expires_in": int((expires - datetime.now(timezone.utc)).total_seconds())}


@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
@router.post("/register", response_model=SignupResponse, status_code=status.HTTP_201_CREATED,
             include_in_schema=False)  # same endpoint under the name the frontend uses
def signup(body: SignupRequest, db: Session = Depends(get_db)):
    """Creates the account and signs the user in (returns a token).
    remember_me=true keeps them signed in for ~30 days instead of ~1 day."""
    if get_user_by_email(db, body.email):
        raise HTTPException(status.HTTP_409_CONFLICT, EMAIL_TAKEN)
    try:
        user = create_user(db, body.email, hash_password(body.password), body.full_name)
    except IntegrityError:  # two signups with the same email at the same moment
        raise HTTPException(status.HTTP_409_CONFLICT, EMAIL_TAKEN)
    return SignupResponse(id=user.id, email=user.email, full_name=user.full_name,
                          **_token_fields(user.id, body.remember_me))


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """remember_me=true keeps the user signed in for ~30 days instead of ~1 day."""
    user = get_user_by_email(db, body.email)
    # Same message for wrong email and wrong password, so attackers can't tell which emails exist.
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    return TokenResponse(**_token_fields(user.id, body.remember_me))