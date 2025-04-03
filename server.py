import os
from contextlib import asynccontextmanager
from typing import Annotated

import dotenv
import psycopg
from fastapi import FastAPI, Body

from retrieve import QueryResult, Retriever


@asynccontextmanager
async def lifespan(app: FastAPI):
    dotenv.load_dotenv()
    with psycopg.connect(os.environ["CONNECTION_STRING"]) as conn:
        app.retriever = Retriever(os.environ["CHROMA_PATH"], conn)
        yield


app = FastAPI(lifespan=lifespan)


@app.post("/search")
def search(
        query: list[str],
        num_results: Annotated[int, Body(gt=0, le=50)] = 10,
) -> list[list[QueryResult]]:
    return app.retriever.batch_search(query, num_results)
