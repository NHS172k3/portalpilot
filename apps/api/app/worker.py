from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from psycopg import Connection

from app.database import connect
from app.tasks import run_task_on_mirror


router = APIRouter(prefix="/worker", tags=["worker"])
Db = Annotated[Connection, Depends(connect)]


@router.post("/tick")
def tick(connection: Db) -> dict:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select id
            from filing_tasks
            where status = 'not_started'
              and form_definition_id is not null
            order by created_at
            limit 1
            """
        )
        task = cursor.fetchone()

    if task is None:
        return {"picked": False, "reason": "No runnable task found"}

    result = run_task_on_mirror(task["id"], connection)
    return {"picked": True, "task_id": task["id"], "result": result}
