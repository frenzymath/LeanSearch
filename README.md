# LeanSearch

[A semantic search engine for Lean 4 projects.](https://arxiv.org/abs/2403.13310)

Also see [Herald](https://arxiv.org/abs/2410.10878v2) for the idea used to translate formal statements into natural language.

## Installation

### Install Python deps

```shell
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### Install Postgres

1. Download PostgreSQL (you can find the installation guide [here](https://www.postgresql.org/download)).
2. Create database:

   ```
   createdb my_database_name
   ```

   Memorize the database name, you will later need to set it in your `.env` file.

### Install jixia

1. Clone the jixia repo: `git clone git@github.com:frenzymath/jixia.git`; `cd jixia`
2. Make sure `lean-toolchain` in jixia and `lean-toolchain` in the project you will be indexing match.  
	 If Lean versions don't match, you will get `"... failed to read file ..., invalid header"` error when you try to index the project.
3. Build jixia: `lake build` (should take around 70s)

### Set up the .env file

1. Copy the `.env.example` file to `.env`:

   ```shell
   cp .env.example .env
   ```

2. Edit the `.env` file and set the required variables according to your setup.

> [!NOTE]  
> We strongly recommend using DeepSeek v3 model for a balance between quality and cost.  
> In this case, `OPENAI_API_KEY` should be set to your DeepSeek api key, `OPENAI_BASE_URL` should be set to `https://api.deepseek.com`, and `OPENAI_MODEL` should be set to `deepseek-chat`.

## Usage

### Indexing

1. **Index your Lean project** (uses jixia, puts results into PostgreSQL)
   
   ```shell
   python -m database <project root> <prefixes>
   ```

    **Options**:
    - `project root`: Path to the project to index. This is where the `lakefile.toml` or `lakefile.lean` is located.
    - `prefixes`: Comma-separated list of module prefixes. A module is indexed only if its module path starts with one of prefixes listed here.  For example, `Init,Lean,Mathlib` will include only `Init.*`, `Lean.*`, and `Mathlib.*` modules.

3. **Create informal descriptions** (uses DeepSeek api, puts results into PostgreSQL)

   ```shell
   python -m database informal
   ```

   Natural-language descriptions can be created using any OpenAI-compatible API, above we advise DeepSeek.

5. **Create embeddings** (uses locally-downloaded `e5-mistral-7b-instruct` model, puts results into Chromadb)

   ```
   python -m database vector-db
   ```

Note that indexing a large project like Mathlib requires a significant amount of both API calls (to create informal descriptions) and computational power (to compute the semantic embedding). Use with caution.

### Searching

To search the database, run:

```shell
python search.py <query1> <query2> ...
```

Note that queries containing whitespaces must be quoted, e.g., `python search.py "Hello world"`.
