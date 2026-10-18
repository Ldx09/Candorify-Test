from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import create_user, get_user_by_email
from app.schemas.auth import LoginRequest, SignupRequest, TokenResponse, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])

EMAIL_TAKEN = "An account with this email already exists"


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(body: SignupRequest, db: Session = Depends(get_db)):
    if get_user_by_email(db, body.email):
        raise HTTPException(status.HTTP_409_CONFLICT, EMAIL_TAKEN)
    try:
        return create_user(db, body.email, hash_password(body.password), body.full_name)
    except IntegrityError:  # two signups with the same email at the same moment
        raise HTTPException(status.HTTP_409_CONFLICT, EMAIL_TAKEN)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = get_user_by_email(db, body.email)
    # Same message for wrong email and wrong password, so attackers can't tell which emails exist.
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    return TokenResponse(access_token=create_access_token(user.id))