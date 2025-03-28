from typing import Annotated

from fastapi import FastAPI, Path

app = FastAPI()


@app.post("/search")
def search(
        query: str,
        num_results: Annotated[int, Path(gt=0, lt=100)]
):
    pass