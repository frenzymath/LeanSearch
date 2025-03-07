import logging
import os

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
main(os.environ["PROJECT_ROOT"], os.environ["LEAN_PREFIXES"])
