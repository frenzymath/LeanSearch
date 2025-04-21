import logging
import os

import dotenv
import jixia

from . import main

dotenv.load_dotenv()
logging.basicConfig(
    filename=os.environ["LOG_FILENAME"] or None,
    filemode=os.environ["LOG_FILEMODE"],
    level=os.environ["LOG_LEVEL"],
)
jixia.run.executable = os.environ["JIXIA_PATH"]

main()
