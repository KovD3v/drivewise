from collections.abc import Generator
from typing import Annotated

import psycopg
from fastapi import Depends, HTTPException, Request

from app.core.config import get_settings
from app.db.pool import DatabaseConfigurationError, DatabaseConnectionPool
from app.repositories.advisor import AdvisorRepository
from app.repositories.documents import DocumentsRepository
from app.repositories.listings import ListingsRepository
from app.repositories.vehicles import VehiclesRepository


def create_database_pool() -> DatabaseConnectionPool:
    return DatabaseConnectionPool(get_settings())


def get_database_pool(request: Request) -> DatabaseConnectionPool:
    pool = getattr(request.app.state, "database_pool", None)
    if pool is None:
        pool = create_database_pool()
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
    except psycopg.OperationalError as error:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed.",
        ) from error


def get_vehicles_repository(
    conn: Annotated[psycopg.Connection, Depends(get_connection)],
) -> VehiclesRepository:
    return VehiclesRepository(conn)


def get_listings_repository(
    conn: Annotated[psycopg.Connection, Depends(get_connection)],
) -> ListingsRepository:
    return ListingsRepository(conn)


def get_documents_repository(
    conn: Annotated[psycopg.Connection, Depends(get_connection)],
) -> DocumentsRepository:
    return DocumentsRepository(conn)


def get_advisor_repository(
    conn: Annotated[psycopg.Connection, Depends(get_connection)],
) -> AdvisorRepository:
    return AdvisorRepository(conn)
