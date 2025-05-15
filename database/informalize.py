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
        cursor.execute(
            """
            SELECT name, signature, informal_name, informal_description
            FROM declaration
            WHERE
                module_name = %s AND index >= %s AND index <= %s
            """,
            (Jsonb(module_name), index - num_neighbor, index + num_neighbor),
        )
        return cursor.fetchall()


def find_dependency(conn: Connection, name: LeanName) -> list[TranslatedItem]:
    with conn.cursor(row_factory=args_row(TranslatedItem)) as cursor:
        cursor.execute(
            """
            SELECT name, signature, informal_name, informal_description
            FROM
                declaration d
                INNER JOIN dependency e ON d.name = e.target
            WHERE
                e.source = %s
            """,
            (Jsonb(name),),
        )
        return cursor.fetchall()


def generate_informal(conn: Connection, batch_size: int = 50, limit_level: int | None = None, limit_num_per_level: int | None = None):
    max_level: int
    if limit_level is None:
        with conn.cursor(row_factory=scalar_row) as cursor:
            max_level = cursor.execute("SELECT MAX(level) FROM level").fetchone() or -1
    else:
        max_level = limit_level

    tasks = []
    with conn.cursor() as cursor, conn.cursor() as insert_cursor:
        for level in range(max_level + 1):
            query = """
            SELECT d.name, d.signature, d.value, d.docstring, d.kind, m.docstring, d.module_name, d.index
            FROM
                declaration d
                INNER JOIN module m ON d.module_name = m.name
                INNER JOIN level l ON d.name = l.symbol_name
            WHERE
                l.level = %s AND
                (d.informal_description IS NULL OR d.informal_name IS NULL)
            """
            if limit_num_per_level:
                cursor.execute(query + " LIMIT %s", (level, limit_num_per_level))
            else:
                cursor.execute(query, (level,))

            while batch := cursor.fetchmany(batch_size):
                env = TranslationEnvironment(model=os.environ["OPENAI_MODEL"])

                async def translate_and_insert(name: LeanName, data: TranslationInput):
                    result = await env.translate(data)
                    if result is None:
                        logger.warning("failed to translate %s", name)
                    else:
                        logger.info("translated %s", name)
                        informal_name, informal_description = result
                        insert_cursor.execute(
                            """
                            UPDATE declaration
                            SET informal_name = %(informal_name)s, informal_description = %(informal_description)s
                            WHERE name = %(name)s
                            """,
                            {
                              "name": Jsonb(name),
                              "informal_name": informal_name,
                              "informal_description": informal_description
                            },
                        )

                tasks.clear()
                for row in batch:
                    name, signature, value, docstring, kind, header, module_name, index = row

                    logger.info("translating %s", name)
                    neighbor = find_neighbor(conn, module_name, index)
                    dependency = find_dependency(conn, name)

                    ti = TranslationInput(
                        name=name,
                        signature=signature,
                        value=value,
                        docstring=docstring,
                        kind=kind,
                        header=header,
                        neighbor=neighbor,
                        dependency=dependency,
                    )
                    tasks.append(translate_and_insert(name, ti))

                async def wait_all():
                    await asyncio.gather(*tasks)
                    await env.client.close()

                asyncio.run(wait_all())
