import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

import app.models  # noqa: F401
from app.config import Settings, get_settings
from app.database import SessionLocal
from app.middleware import configure_middleware
from app.routers.index import api_router
from app.seed.user_seed import seed_default_manager_if_enabled

settings = get_settings()
logger = logging.getLogger(__name__)
FRONTEND_DIST_DIR = Path(__file__).resolve().parents[2] / "frontend" / "dist"


_INSECURE_SECRET_KEYS = {"", "change-this-secret"}
_INSECURE_DEFAULT_PASSWORDS = {"", "ChangeMe123!"}
_LOCAL_DATABASE_HOSTS = ("localhost", "127.0.0.1")


def validate_production_config(config: Settings) -> None:
    """Refuse to boot in production with insecure scaffolding defaults.

    The check only fires when ENVIRONMENT is not 'development'. Each failure
    names the offending env var so Render logs explain what to fix.
    """
    if config.environment.lower() == "development":
        return

    failures: list[str] = []

    if config.secret_key in _INSECURE_SECRET_KEYS:
        failures.append(
            "SECRET_KEY is unset or still the scaffold default 'change-this-secret'. "
            "Set SECRET_KEY to a long random string in the environment."
        )

    db_url = (config.database_url or "").strip()
    if not db_url:
        failures.append("DATABASE_URL is empty. Set it to your Postgres connection string.")
    elif any(host in db_url for host in _LOCAL_DATABASE_HOSTS):
        failures.append(
            "DATABASE_URL still points at localhost. In a non-development environment "
            "this must point at your managed Postgres (e.g. Neon)."
        )

    if config.seed_default_manager and config.default_manager_password in _INSECURE_DEFAULT_PASSWORDS:
        failures.append(
            "SEED_DEFAULT_MANAGER is true with the scaffold password 'ChangeMe123!'. "
            "Either disable seeding (SEED_DEFAULT_MANAGER=false) or set a strong "
            "DEFAULT_MANAGER_PASSWORD."
        )

    if failures:
        bullet_list = "\n  - ".join(failures)
        raise RuntimeError(
            "Refusing to start in non-development environment with insecure defaults:\n  - "
            f"{bullet_list}"
        )


validate_production_config(settings)


class SinglePageApplicationFiles(StaticFiles):
    async def get_response(self, path: str, scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404:
                return await super().get_response("index.html", scope)
            raise


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
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

configure_middleware(app)
app.include_router(api_router, prefix="/api")


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(_: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.exception("Database operation failed.", exc_info=exc)
    return JSONResponse(
        status_code=503,
        content={"detail": "Database operation failed. Confirm migrations and database connectivity."},
    )


if FRONTEND_DIST_DIR.exists():
    app.mount("/", SinglePageApplicationFiles(directory=FRONTEND_DIST_DIR, html=True), name="frontend")
else:
    @app.get("/", tags=["root"])
    def read_root() -> dict[str, str]:
        return {
            "app": settings.app_name,
            "message": "UCMB HMIS 105 DQA Platform backend is running.",
        }
