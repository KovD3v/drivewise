from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

import psycopg
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.api.dependencies import create_database_pool, get_connection
from app.api.routers import (
    advisor,
    documents,
    guided_decisions,
    listings,
    search,
    vehicles,
)
from app.core.config import get_settings
from app.core.version import (
    SERVICE_NAME,
    get_api_version,
    get_git_commit,
    get_schema_version,
)
from app.schemas.version import VersionResponse
from app.services.advisor.scoring import SCORING_VERSION


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.database_pool = create_database_pool()
    try:
        yield
    finally:
        app.state.database_pool.close()


settings = get_settings()
app = FastAPI(
    title="Drivewise API", lifespan=lifespan, root_path=settings.api_root_path
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.api_cors_origins),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(vehicles.router)
app.include_router(listings.router)
app.include_router(documents.router)
app.include_router(search.router)
app.include_router(advisor.router)
app.include_router(guided_decisions.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "drivewise-api"}


@app.get("/version", response_model=VersionResponse)
def version() -> VersionResponse:
    return VersionResponse(
        service=SERVICE_NAME,
        api_version=get_api_version(),
        git_commit=get_git_commit(),
        scoring_version=SCORING_VERSION,
        schema_version=get_schema_version(),
    )


@app.get("/ready")
def ready(conn: Annotated[psycopg.Connection, Depends(get_connection)]) -> dict[str, str]:
    try:
        conn.execute("SELECT 1").fetchone()
    except psycopg.Error as error:
        raise HTTPException(status_code=503, detail="Database is not ready.") from error

    return {"status": "ready", "service": "drivewise-api", "database": "ok"}
