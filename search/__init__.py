import os

import psycopg
from jixia.structs import pp_name
from pydantic import TypeAdapter

from search.retrieve import Retriever, QueryResult


def main(query: list[str], num_results: int, json_output: bool):
    with psycopg.connect(os.environ["CONNECTION_STRING"], autocommit=True) as conn:
        retriever = Retriever(os.environ["CHROMA_PATH"], conn)
        results = retriever.batch_search(query, num_results)
        if json_output:
            print(TypeAdapter(list[list[QueryResult]]).dump_json(results))
        else:
            for q, r in zip(query, results):
                print("Results for", q)
                for i, record in enumerate(r):
                    print(str(i) + ":")
                    print(record.kind, pp_name(record.name), record.signature)
                    print(record.informal_name + ":", record.informal_description)
                    print()
                print("---")
