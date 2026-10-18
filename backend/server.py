import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import get_current_user
from app.api.routes import account, auth, bills, letters, translate
from app.core.config import settings
from app.core.database import Base, check_connection, engine
from app.core.errors import register_error_handlers
from app.core.http_security import add_http_security
from app.models import bill_record  # noqa: F401  (registers the bills tables for create_all)
from app.models.user import User
from app.schemas.auth import UserOut
from app.services.retention import RetentionScheduler

logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s: %(message)s")
retention = RetentionScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    check_connection()  # stops the server with a clear message if the database is unreachable
    Base.metadata.create_all(bind=engine)  # creates missing tables; never changes existing ones
    retention.start()  # deletes expired bills now and every RETENTION_SWEEP_MINUTES
    yield
    retention.stop()


app = FastAPI(
    title="Candorify API", version="0.7.0", lifespan=lifespan,
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings.docs_enabled else None,
)
register_error_handlers(app)
add_http_security(app)  # HTTPS redirect in production + security headers

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


@protected.get("/me", response_model=UserOut, tags=["account"])
def me(user: User = Depends(get_current_user)):
    """Returns the logged-in user. Requires: Authorization: Bearer <token>"""
    return user


protected.include_router(account.router)    # DELETE /api/me
protected.include_router(bills.router)      # /api/bills (list, create, sample, get, delete, check, translate)
protected.include_router(translate.router)  # /api/translate?code=
protected.include_router(letters.router)    # /api/letters

app.include_router(protected)