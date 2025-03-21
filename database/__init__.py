import os
from argparse import ArgumentParser

import psycopg
from jixia import LeanProject
from jixia.structs import parse_name

from .informalize import generate_informal
from .jixia_db import load_data
from .vector_db import create_vector_db


def main():
    parser = ArgumentParser()
    subparser = parser.add_subparsers()
    jixia_parser = subparser.add_parser("jixia")
    jixia_parser.set_defaults(command="jixia")
    jixia_parser.add_argument("project_root", help="Project to be indexed")
    jixia_parser.add_argument(
        "prefixes",
        help="Comma-separated list of module prefixes to be included in the index; e.g., Init,Mathlib",
    )
    informal_parser = subparser.add_parser("informal")
    informal_parser.set_defaults(command="informal")
    informal_parser.add_argument(
        "--limit-level", type=int,
        help="Limit max level. Used for testing.",
    )
    informal_parser.add_argument(
        "--limit-num-per-level", type=int,
        help="Limit max number of items per level. Used for testing.",
    )
    vector_db_parser = subparser.add_parser("vector-db")
    vector_db_parser.set_defaults(command="vector-db")
    vector_db_parser.add_argument("--batch-size", type=int, default=8)

    args = parser.parse_args()

    with psycopg.connect(os.environ["CONNECTION_STRING"], autocommit=True) as conn:
        if args.command == "jixia":
            project = LeanProject(args.project_root)
            prefixes = [parse_name(p) for p in args.prefixes.split(",")]
            load_data(project, prefixes, conn)
        elif args.command == "informal":
            generate_informal(conn, limit_level=args.limit_level, limit_num_per_level=args.limit_num_per_level)
        elif args.command == "vector-db":
            create_vector_db(conn, os.environ["CHROMA_PATH"], batch_size=args.batch_size)
