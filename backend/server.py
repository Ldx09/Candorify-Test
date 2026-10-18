from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import get_current_user
from app.api.routes import auth, bills, codes
from app.core.config import settings
from app.core.database import Base, check_connection, engine
from app.core.errors import register_error_handlers
from app.models import bill_record  # noqa: F401  (registers the bills tables for create_all)
from app.models.user import User
from app.schemas.auth import UserOut


@asynccontextmanager
async def lifespan(app: FastAPI):
    check_connection()  # stops the server with a clear message if the database is unreachable
    Base.metadata.create_all(bind=engine)  # creates missing tables; never changes existing ones
    yield


app = FastAPI(title="Candorify API", version="0.4.0", lifespan=lifespan)
register_error_handlers(app)

# CORS: only the frontend origins listed in settings.CORS_ORIGINS may call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# ---- Public routes (no login needed) ----
app.include_router(auth.router)  # /api/auth/signup, /api/auth/login


@app.get("/health")
def health():
    return {"status": "ok"}


# ---- Protected app routes (login required) ----
# requireAuth: every route added to `protected` returns 401 unless a valid token is sent.
protected = APIRouter(prefix="/api", dependencies=[Depends(get_current_user)])


@protected.get("/me", response_model=UserOut, tags=["auth"])
def me(user: User = Depends(get_current_user)):
    """Returns the logged-in user. Requires: Authorization: Bearer <token>"""
    return user


protected.include_router(bills.router)  # /api/bills, /api/bills/{id}, /api/bills/{id}/check
protected.include_router(codes.router)  # /api/codes/{code}
app.include_router(protected)