import os
from typing import Annotated

import dotenv
import psycopg
import uvicorn
from fastapi import FastAPI, Body

from retrieve import QueryResult, Retriever

app = FastAPI()

@app.post("/search")
def search(
        query: list[str],
        num_results: Annotated[int, Body(gt=0, le=50)] = 10,
) -> list[list[QueryResult]]:
    return retriever.batch_search(query, num_results)


if __name__ == '__main__':
    dotenv.load_dotenv()
    with psycopg.connect(os.environ["CONNECTION_STRING"]) as conn:
        retriever = Retriever(os.environ["CHROMA_PATH"], conn)
        uvicorn.run(app)
