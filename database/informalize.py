import asyncio
import logging
import os

from jixia.structs import LeanName
from psycopg import Cursor
from psycopg.types.json import Jsonb

from .translate import TranslatedItem, TranslationInput, TranslationEnvironment

logger = logging.getLogger(__name__)


def find_neighbor(cursor: Cursor, module_name: LeanName, index: int) -> list[TranslatedItem]:
    cursor.execute("""
        SELECT d.name, d.signature, i.name, i.description
        FROM
            declaration d
            LEFT JOIN informal i ON d.name = i.symbol_name
        WHERE
            d.module_name = %s AND d.index >= %s AND d.index <= %s
    """, (Jsonb(module_name), index - 2, index + 2))
    return [TranslatedItem(*row) for row in cursor]


def find_dependency(cursor: Cursor, name: LeanName) -> list[TranslatedItem]:
    cursor.execute("""
        SELECT d.name, d.signature, i.name, i.description
        FROM
            declaration d
            INNER JOIN dependency e ON d.name = e.target
            LEFT JOIN informal i ON d.name = i.symbol_name
        WHERE
            e.source = %s
    """, (Jsonb(name),))
    return [TranslatedItem(*row) for row in cursor]


async def run_multiple(tasks):
    return await asyncio.gather(*tasks)


def generate_informal(cursor: Cursor):
    env = TranslationEnvironment(model=os.environ["OPENAI_MODEL"])

    cursor.execute("""
        SELECT MAX(level) FROM level
    """)
    max_level, = cursor.fetchone()

    names = []
    tasks = []

    for l in range(max_level):
        cursor.execute("""
            SELECT s.name, d.signature, d.value, d.docstring, d.kind, m.docstring, d.module_name, d.index
            FROM
                symbol s
                INNER JOIN declaration d ON s.name = d.name
                INNER JOIN module m ON s.module_name = m.name
                INNER JOIN level l ON s.name = l.symbol_name
            WHERE l.level = %s
        """, (l,))

        names.clear()
        tasks.clear()
        rows = cursor.fetchall()
        for row in rows:
            basic, (module_name, index) = row[:-2], row[-2:]
            name = basic[0]
            logger.info("translating %s", name)
            neighbor = find_neighbor(cursor, module_name, index)
            dependency = find_dependency(cursor, name)
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
