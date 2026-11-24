from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import psycopg
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.api.dependencies import ConnectionDep, create_database_pool
from app.api.routers import (
    advisor,
    documents,
    guided_decisions,
    listings,
    search,
    vehicles,
)
from app.core.config import Settings, get_settings
from app.core.version import (
    SERVICE_NAME,
    get_api_version,
    get_git_commit,
    get_schema_version,
)
from app.schemas.version import VersionResponse
from app.services.advisor.scoring import SCORING_VERSION


PRIVATE_NO_STORE = "private, no-store"
PUBLIC_CATALOG_CACHE = "public, max-age=60, stale-while-revalidate=300"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.database_pool = create_database_pool(
        getattr(app.state, "settings", None)
    )
    try:
        yield
    finally:
        app.state.database_pool.close()


def _path_under(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(prefix + "/")


class CacheControlMiddleware:
    """Sets Cache-Control on personal and catalog responses.

    Guided decisions are personal, so they are never stored. Catalog reads
    change at most per import, so successful GETs may be cached briefly.
    """

    def __init__(self, app: ASGIApp, root_path: str = "") -> None:
        self.app = app
        self.root_path = root_path

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope["path"]
        # Production serves under a prefix ("/api"); match on the bare path.
        if self.root_path and _path_under(path, self.root_path):
            path = path[len(self.root_path) :] or "/"
        is_personal = _path_under(path, "/guided-decisions")
        is_catalog_read = scope["method"] == "GET" and _path_under(path, "/vehicles")
        if not (is_personal or is_catalog_read):
            await self.app(scope, receive, send)
            return

        async def send_with_cache_control(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                has_cache_control = any(
                    name.lower() == b"cache-control" for name, _ in headers
                )
                value = None
                if is_personal:
                    value = PRIVATE_NO_STORE
                elif message["status"] == 200 and not has_cache_control:
                    value = PUBLIC_CATALOG_CACHE
                if value is not None:
                    headers = [
                        (name, val)
                        for name, val in headers
                        if name.lower() != b"cache-control"
                    ]
                    headers.append((b"cache-control", value.encode("latin-1")))
                    message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_cache_control)


def create_app(settings: Settings) -> FastAPI:
    internal = settings.enable_internal_routes
    application = FastAPI(
        title="Drivewise API",
        lifespan=lifespan,
        root_path=settings.api_root_path,
        # Outside local/test the schema and interactive docs are not public.
        docs_url="/docs" if internal else None,
        redoc_url="/redoc" if internal else None,
        openapi_url="/openapi.json" if internal else None,
    )
    application.state.settings = settings

    application.add_middleware(
        CacheControlMiddleware, root_path=settings.api_root_path
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.api_cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

    application.include_router(vehicles.router)
    application.include_router(advisor.router)
    application.include_router(guided_decisions.router)
    if internal:
        application.include_router(listings.router)
        application.include_router(documents.router)
        application.include_router(search.router)

    application.add_api_route("/health", health, methods=["GET"])
    application.add_api_route(
        "/version", version, methods=["GET"], response_model=VersionResponse
    )
    application.add_api_route("/ready", ready, methods=["GET"])
    return application


def health() -> dict[str, str]:
    return {"status": "ok", "service": "drivewise-api"}


def version() -> VersionResponse:
    return VersionResponse(
        service=SERVICE_NAME,
        api_version=get_api_version(),
        git_commit=get_git_commit(),
        scoring_version=SCORING_VERSION,
        schema_version=get_schema_version(),
    )


def ready(conn: ConnectionDep) -> dict[str, str]:
    try:
        conn.execute("SELECT 1").fetchone()
    except psycopg.Error as error:
        raise HTTPException(status_code=503, detail="Database is not ready.") from error

    return {"status": "ready", "service": "drivewise-api", "database": "ok"}


settings = get_settings()
app = create_app(settings)
