import os
import uuid
from contextlib import asynccontextmanager
from typing import Annotated

import dotenv
import psycopg
from fastapi import FastAPI, Body, Response, Cookie
from jixia.structs import LeanName
from psycopg import Connection
from psycopg.rows import scalar_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.requests import Request

from augment import Augmentor
from retrieve import QueryResult, Retriever, Record


@asynccontextmanager
async def lifespan(app: FastAPI):
    dotenv.load_dotenv()
    with ConnectionPool(
            os.environ["CONNECTION_STRING"],
            kwargs={"autocommit": True},
            check=ConnectionPool.check_connection,
    ) as pool:
        app.augmentor = Augmentor(os.environ["OPENAI_MODEL"])
        app.retriever = Retriever(os.environ["CHROMA_PATH"], None)
        app.pool = pool
        yield


limiter = Limiter(key_func=get_remote_address, default_limits=["1/second"])
app = FastAPI(lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.middleware("http")
async def set_connection(request: Request, call_next):
    with app.pool.connection() as conn:
        app.retriever.conn = conn
        return await call_next(request)


app.add_middleware(SlowAPIMiddleware)


@app.post("/search")
def search(
        response: Response,
        query: list[str],
        num_results: Annotated[int, Body(gt=0, le=150)] = 10,
) -> list[list[QueryResult]]:
    if len(query) == 1:
        with app.retriever.conn.cursor(row_factory=scalar_row) as cursor:
            cursor.execute("""
                           INSERT INTO leansearch.query(id, query, time)
                           VALUES (GEN_RANDOM_UUID(), %s, NOW())
                           RETURNING id
                           """, (query[0],))
            session_id = cursor.fetchone()
            response.set_cookie("session", str(session_id))
    else:
        with app.retriever.conn.cursor() as cursor:
            cursor.executemany("""
                               INSERT INTO leansearch.query(id, query, time)
                               VALUES (GEN_RANDOM_UUID(), %s, NOW())
                               """, [(q,) for q in query])

    return app.retriever.batch_search(query, num_results)


@app.post("/fetch")
@limiter.limit("10/second")
def fetch(request: Request, query: list[LeanName]) -> list[Record]:
    return app.retriever.batch_fetch(query)


@app.post("/augment")
@limiter.limit("15/minute")
async def augment(request: Request, query: Annotated[str, Body()]) -> str:
    augmented = await app.augmentor.augment(query)
    return augmented


class Feedback(BaseModel):
    declaration: LeanName
    action: str
    cancel: bool | None = None


@app.post("/feedback")
async def feedback(session: Annotated[str, Cookie()], body: Feedback):
    query_id = uuid.UUID(session)
    if body.cancel:
        with app.retriever.conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM leansearch.feedback WHERE query_id = %s AND declaration_name = %s",
                (query_id, Jsonb(body.declaration))
            )
    else:
        with app.retriever.conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO leansearch.feedback(query_id, declaration_name, action) VALUES (%s, %s, %s)",
                (query_id, Jsonb(body.declaration), body.action)
            )
