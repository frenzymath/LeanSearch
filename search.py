import os
from argparse import ArgumentParser

import dotenv
import psycopg
from jixia.structs import pp_name
from pydantic import TypeAdapter

from retrieve import Retriever, QueryResult


def main(query: list[str], num_results: int, json_output: bool):
    with psycopg.connect(os.environ["CONNECTION_STRING"], autocommit=True) as conn:
        retriever = Retriever(os.environ["CHROMA_PATH"], conn)
        results = retriever.batch_search(query, num_results)
        if json_output:
            print(TypeAdapter(list[list[QueryResult]]).dump_json(results).decode())
        else:
            for q, rs in zip(query, results):
                print("Results for", q)
                for i, r in enumerate(rs):
                    result = r.result
                    print(str(i) + ":")
                    print("Distance:", r.distance)
                    print(result.kind, pp_name(result.name), result.signature)
                    print("Elaborated type:", result.type)
                    print(result.informal_name + ":", result.informal_description)
                    print()
                print("---")


if __name__ == "__main__":
    dotenv.load_dotenv()
    parser = ArgumentParser()
    parser.add_argument("-n", "--num", type=int, help="Number of results per each query", default=5)
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    parser.add_argument("query", nargs="+", help="Any number of query strings")
    args = parser.parse_args()
    main(args.query, args.num, args.json)
