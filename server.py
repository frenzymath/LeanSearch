import os
from contextlib import asynccontextmanager
from typing import Annotated

import dotenv
import psycopg
from fastapi import FastAPI, Body
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from retrieve import QueryResult, Retriever


@asynccontextmanager
async def lifespan(app: FastAPI):
    dotenv.load_dotenv()
    with psycopg.connect(os.environ["CONNECTION_STRING"]) as conn:
        app.retriever = Retriever(os.environ["CHROMA_PATH"], conn)
        yield


limiter = Limiter(key_func=get_remote_address, default_limits=["1/second"])
app = FastAPI(lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


@app.post("/search")
def search(
        query: list[str],
        num_results: Annotated[int, Body(gt=0, le=50)] = 10,
) -> list[list[QueryResult]]:
    return app.retriever.batch_search(query, num_results)
