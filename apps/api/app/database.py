from collections.abc import Iterator

import psycopg
from fastapi import HTTPException
from psycopg.rows import dict_row

from app.config import get_settings


def connect() -> Iterator[psycopg.Connection]:
    db_url = get_settings().db_url
    if not db_url:
        raise HTTPException(status_code=503, detail="Database is not configured")

    with psycopg.connect(db_url, row_factory=dict_row, prepare_threshold=None) as connection:
        yield connection
