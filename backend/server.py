from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import auth
from app.core.database import Base, engine
from app.core.errors import register_error_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Creates the users table if it doesn't exist yet. Never changes an existing table.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Candorify API", version="0.2.0", lifespan=lifespan)
register_error_handlers(app)

app.include_router(auth.router)


@app.get("/health")
def health():
    return {"status": "ok"}