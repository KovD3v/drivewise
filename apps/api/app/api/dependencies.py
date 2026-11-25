from collections.abc import Generator
from typing import Annotated

import psycopg
from fastapi import Depends, HTTPException, Request

from app.core.config import Settings, get_settings
from app.db.pool import (
    DatabaseConfigurationError,
    DatabaseConnectionPool,
    DatabasePoolClosedError,
    DatabasePoolTimeoutError,
)
from app.repositories.advisor import AdvisorRepository
from app.repositories.documents import DocumentsRepository
from app.repositories.guided_decisions import GuidedDecisionsRepository
from app.repositories.listings import ListingsRepository
from app.repositories.vehicles import VehiclesRepository


def create_database_pool(settings: Settings | None = None) -> DatabaseConnectionPool:
    return DatabaseConnectionPool(settings or get_settings())


def get_app_settings(request: Request) -> Settings:
    return getattr(request.app.state, "settings", None) or get_settings()


def get_database_pool(request: Request) -> DatabaseConnectionPool:
    pool = getattr(request.app.state, "database_pool", None)
    # A pool closed by lifespan shutdown refuses connections, so a later request
    # on the same app object (tests reuse it) gets a fresh one.
    if pool is None or pool.closed:
        pool = create_database_pool(get_app_settings(request))
        request.app.state.database_pool = pool
    return pool


def get_connection(
    pool: Annotated[DatabaseConnectionPool, Depends(get_database_pool)],
) -> Generator[psycopg.Connection, None, None]:
    try:
        with pool.connection() as conn:
            yield conn
    except DatabaseConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except (DatabasePoolTimeoutError, DatabasePoolClosedError) as error:
        raise HTTPException(
            status_code=503,
            detail="Database is busy. Try again shortly.",
        ) from error
    except psycopg.OperationalError as error:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed.",
        ) from error


# scope="function" runs the dependency's exit code (commit or rollback) when
# the endpoint returns, before FastAPI sends the response. With the default
# "request" scope a failed commit would still reach the client as a 2xx.
# Every consumer must use this alias: a different Depends spec has a different
# cache key and would open a second connection in the same request.
ConnectionDep = Annotated[
    psycopg.Connection, Depends(get_connection, scope="function")
]


def require_internal_routes(
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> None:
    """Hide internal/debug endpoints outside local and test environments."""
    if not settings.enable_internal_routes:
        raise HTTPException(status_code=404, detail="Not Found")


def get_vehicles_repository(
    conn: ConnectionDep,
) -> VehiclesRepository:
    return VehiclesRepository(conn)


def get_listings_repository(
    conn: ConnectionDep,
) -> ListingsRepository:
    return ListingsRepository(conn)


def get_documents_repository(
    conn: ConnectionDep,
) -> DocumentsRepository:
    return DocumentsRepository(conn)


def get_advisor_repository(
    conn: ConnectionDep,
) -> AdvisorRepository:
    return AdvisorRepository(conn)


def get_guided_decisions_repository(
    conn: ConnectionDep,
) -> GuidedDecisionsRepository:
    return GuidedDecisionsRepository(conn)
