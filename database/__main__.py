import logging
import os
from argparse import ArgumentParser

import dotenv
import jixia

from . import main

dotenv.load_dotenv()
logging.basicConfig(
    filename=os.environ.get("LOG_FILENAME"),
    filemode=os.environ.get("LOG_FILEMODE", "w"),
    level=os.environ.get("LOG_LEVEL", "WARNING").upper(),
)
jixia.run.executable = os.environ["JIXIA_PATH"]

parser = ArgumentParser(description="Index a project for LeanSearch")
parser.add_argument("project_root", help="Project to be indexed")
parser.add_argument("prefixes", help="Comma-separated list of module prefixes to be included in the index; e.g., Init,Mathlib")
args = parser.parse_args()
main(args.project_root, args.prefixes)
