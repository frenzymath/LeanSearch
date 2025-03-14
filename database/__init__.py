import os

import psycopg
from jixia import LeanProject
from jixia.structs import AnyPath, parse_name

from .jixia_db import load_data
from .informalize import generate_informal
from .vector_db import create_vector_db


def main(project_root: AnyPath, prefixes: str):
    project = LeanProject(project_root)
    prefixes = [parse_name(p) for p in prefixes.split(",")]
    conn: psycopg.connection.Connection
    with psycopg.connect(os.environ["CONNECTION_STRING"], autocommit=True) as conn:
        with conn.cursor() as cur:
            load_data(project, prefixes, cur)
            generate_informal(cur)
            create_vector_db(cur, os.environ["CHROMA_PATH"], batch_size=8)
