# LeanSearch

[A semantic search engine for Lean 4 projects.](https://arxiv.org/abs/2403.13310)

Also see [Herald](https://arxiv.org/abs/2410.10878v2) for the idea used to translate formal statements into natural language.

### Prerequisite

LeanSearch depends on [jixia](https://github.com/frenzymath/jixia) for static analysis.  You need to download and build it with `lake build`.

LeanSearch utilizes PostgreSQL as the relational database.  You can find the installation guide [here](https://www.postgresql.org/download/).

You need to create the PostgreSQL database before running LeanSearch with the command `createdb <database-name>`.

It is recommended to install LeanSearch in a Python virtual environment.
```shell
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### Indexing a project

To use LeanSearch with a project, it must first be indexed.  Run `python -m database` to create the index.

Note that indexing a large project like Mathlib requires a significant amount of both API call cost and computational power.  Use with caution. 

### Searching

Run `python -m search <query1> <query2> ...` to search the database.  Note that queries containing whitespaces must be quoted, e.g., `python -m "Hello world"`

### Environment variables

LeanSearch is configured through multiple environment variables.  All the variables listed below are **required** unless otherwise noted. 

- `JIXIA_PATH`: executable path of `jixia`.  For example, suppose jixia was downloaded to `/home/tony/jixia` then `JIXIA_PATH` should be set to `/home/tony/jixia/.lake/build/bin/jixia`.
- `PROJECT_ROOT`: path to the project to be indexed, e.g., `/home/tony/mathlib4`.
- `LEAN_SYSROOT`: system root of your Lean 4 installation.  This can be found out by running `lake env` and copy the `LEAN_SYSROOT` line.
- `LEAN_PREFIXES`
- `CONNECTION_STRING`: [connection string](https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING) used to connect to the PostgreSQL database. For a simple local setup, set this to `dbname=<database name>`.
- `CHROMA_PATH`: location to store ChromaDB files.
- `OPENAI_API_KEY`: OpenAI-compatible API key.
- `OPENAI_BASE_URL`: OpenAI-compatible API endpoint.
- `OPENAI_MODEL`: model to use.
- `EMBEDDING_DEVICE`: [torch device](https://pytorch.org/docs/stable/tensor_attributes.html#torch.device) to compute the embedding.  Default is "cpu".
- `LOG_FILENAME`: name of the log file.  Default is logging to console.
- `LOG_FILEMODE`: log file mode.  "w" for overwriting and "a" for appending.  Default is "w".
- `LOG_LEVEL`: log level.  Default is "WARNING". 

We strongly recommend using DeepSeek v3 model for a balance between quality and cost.  In this case, `OPENAI_BASE_URL` should be set to `https://api.deepseek.com` and `OPENAI_MODEL` is `deepseek-chat`.

##### Using dotenv

LeanSearch supports [dotenv](https://github.com/theskumar/python-dotenv) for easy environment variable management.  You can create a file in this directory named `.env` and put environment variables there.  As an example, this repository is developed under these settings:
```shell
JIXIA_PATH=".../jixia/.lake/build/bin/jixia"
PROJECT_ROOT=".../mathlib4"
LEAN_SYSROOT=".../.elan/toolchains/leanprover--lean4---v4.13.0"
LEAN_PREFIXES="Mathlib,Init,Lean"
CONNECTION_STRING="dbname=mathlib4"
CHROMA_PATH="chroma"
OPENAI_API_KEY=<redacted>
OPENAI_BASE_URL="https://api.deepseek.com"
OPENAI_MODEL="deepseek-chat"
LOGGING_LEVEL="INFO"
```
