from argparse import ArgumentParser

import dotenv

from . import main


dotenv.load_dotenv()
parser = ArgumentParser()
parser.add_argument("-n", "--num", type=int, help="Number of results per each query", default=5)
parser.add_argument("--json", action="store_true", help="Output in JSON format")
parser.add_argument("query", nargs="*", help="Any number of query strings")
args = parser.parse_args()
main(args.query, args.num, args.json)
