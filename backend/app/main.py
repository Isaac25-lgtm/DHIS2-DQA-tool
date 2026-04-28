import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

import app.models  # noqa: F401
from app.config import get_settings
from app.database import SessionLocal
from app.middleware import configure_middleware
from app.routers.index import api_router
from app.seed.user_seed import seed_default_manager_if_enabled

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        with SessionLocal() as session:
            if seed_default_manager_if_enabled(session):
                session.commit()
    except Exception as exc:  # pragma: no cover - defensive startup logging
        logger.warning("Default manager seed skipped during startup: %s", exc)
    yield

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

configure_middleware(app)
app.include_router(api_router, prefix="/api")


@app.get("/", tags=["root"])
def read_root() -> dict[str, str]:
    return {
        "app": settings.app_name,
        "message": "UCMB HMIS 105 DQA Platform backend is running.",
    }
