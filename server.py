import os
from typing import Annotated

import dotenv
import psycopg
from fastapi import FastAPI, Body

from retrieve import QueryResult, Retriever

dotenv.load_dotenv()
conn = psycopg.connect(os.environ["CONNECTION_STRING"])
retriever = Retriever(os.environ["CHROMA_PATH"], conn)
app = FastAPI()


@app.post("/search")
def search(
        query: list[str],
        num_results: Annotated[int, Body(gt=0, le=50)] = 10,
) -> list[list[QueryResult]]:
    return retriever.batch_search(query, num_results)
