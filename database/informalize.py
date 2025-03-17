import asyncio
import logging
import os

from jixia.structs import LeanName
from psycopg import Connection
from psycopg.rows import scalar_row, args_row
from psycopg.types.json import Jsonb

from .translate import TranslatedItem, TranslationInput, TranslationEnvironment

logger = logging.getLogger(__name__)


def find_neighbor(conn: Connection, module_name: LeanName, index: int, num_neighbor: int = 2) -> list[TranslatedItem]:
    with conn.cursor(row_factory=args_row(TranslatedItem)) as cursor:
        cursor.execute("""
            SELECT d.name, d.signature, i.name, i.description
            FROM
                declaration d
                LEFT JOIN informal i ON d.name = i.symbol_name
            WHERE
                d.module_name = %s AND d.index >= %s AND d.index <= %s
        """, (Jsonb(module_name), index - num_neighbor, index + num_neighbor))
    return cursor.fetchall()


def find_dependency(conn: Connection, name: LeanName) -> list[TranslatedItem]:
    with conn.cursor(row_factory=args_row(TranslatedItem)) as cursor:
        cursor.execute("""
            SELECT d.name, d.signature, i.name, i.description
            FROM
                declaration d
                INNER JOIN dependency e ON d.name = e.target
                LEFT JOIN informal i ON d.name = i.symbol_name
            WHERE
                e.source = %s
        """, (Jsonb(name),))
    return cursor.fetchall()


async def run_multiple(tasks):
    return await asyncio.gather(*tasks)


def generate_informal(conn: Connection, limit_level: int | None = None, limit_num_per_level: int | None = None):
    env = TranslationEnvironment(model=os.environ["OPENAI_MODEL"])

    if limit_level is None:
        with conn.cursor(row_factory=scalar_row) as cursor:
            cursor.execute("""
                SELECT MAX(level) FROM level
            """)
            limit_level = cursor.fetchone()

    names = []
    tasks = []

    with conn.cursor() as cursor:
        for l in range(limit_level):
            query = """
                SELECT s.name, d.signature, d.value, d.docstring, d.kind, m.docstring, d.module_name, d.index
                FROM
                    symbol s
                    INNER JOIN declaration d ON s.name = d.name
                    INNER JOIN module m ON s.module_name = m.name
                    INNER JOIN level l ON s.name = l.symbol_name
                WHERE l.level = %s
            """
            if limit_num_per_level:
                query += f" LIMIT {limit_num_per_level}"
            cursor.execute(query, (l,))

            names.clear()
            tasks.clear()
            for row in cursor:
                basic, (module_name, index) = row[:-2], row[-2:]
                name = basic[0]
                logger.info("translating %s", name)
                neighbor = find_neighbor(conn, module_name, index)
                dependency = find_dependency(conn, name)
                data = TranslationInput(*basic, neighbor, dependency)
                names.append(name)
                tasks.append(env.translate(data))

            results = asyncio.run(run_multiple(tasks))
            values = []
            for name, result in zip(names, results):
                if results is None:
                    logger.warning("failed to translate %s", name)
                else:
                    values.append((Jsonb(name),) + result)
            cursor.executemany("""
                INSERT INTO informal (symbol_name, name, description)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
            """, values)
