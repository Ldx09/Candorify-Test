"""Account endpoints. Protected."""
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.services.retention import delete_user_and_data

router = APIRouter(tags=["account"])


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_account(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """One-tap deletion: permanently deletes the account, all its bills and all bill lines.
    The token stops working immediately (the user no longer exists)."""
    delete_user_and_data(db, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)