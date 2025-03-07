import logging
import os
from collections.abc import Iterable
from pathlib import Path
from typing import LiteralString

from jixia import LeanProject
from jixia.structs import LeanName, Symbol, Declaration, is_internal
from psycopg import Cursor
from psycopg.errors import DuplicateObject
from psycopg.types.json import Jsonb

logger = logging.getLogger(__name__)


def create_table(cur: Cursor):
    sql: list[LiteralString] = [
        """
        CREATE TABLE IF NOT EXISTS module (
            name JSONB PRIMARY KEY,
            content BYTEA NOT NULL,
            docstring TEXT
        )
        """,

        """
        CREATE TYPE declaration_kind AS ENUM (
            'abbrev',
            'axiom',
            'classInductive',
            'definition',
            'example',
            'inductive',
            'instance',
            'opaque',
            'structure',
            'theorem',
            'proofWanted'
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS symbol (
            name JSONB PRIMARY KEY,
            module_name JSONB REFERENCES module(name) NOT NULL,
            type TEXT NOT NULL,
            is_prop BOOLEAN NOT NULL
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS declaration (
            module_name JSONB REFERENCES module(name) NOT NULL,
            index INTEGER NOT NULL,
            name JSONB UNIQUE REFERENCES symbol(name),
            visible BOOLEAN NOT NULL,
            docstring TEXT,
            kind declaration_kind NOT NULL,
            signature TEXT NOT NULL,
            value TEXT,
            PRIMARY KEY (module_name, index)
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS dependency (
            source JSONB REFERENCES symbol(name) NOT NULL,
            target JSONB REFERENCES symbol(name) NOT NULL,
            on_type BOOLEAN NOT NULL,
            PRIMARY KEY (source, target, on_type)
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS level (
            symbol_name JSONB PRIMARY KEY REFERENCES symbol(name) NOT NULL,
            level INTEGER NOT NULL
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS informal (
            symbol_name JSONB PRIMARY KEY REFERENCES symbol(name) NOT NULL,
            name TEXT NOT NULL,
            description TEXT NOT NULL
        )
        """,
    ]

    for s in sql:
        try:
            cur.execute(s)
        except DuplicateObject:
            pass


def load_data(project: LeanProject, prefixes: list[LeanName], cursor: Cursor):
    def load_module(data: Iterable[LeanName], base_dir: Path):
        values = ((
            Jsonb(m),
            project.path_of_module(m, base_dir).read_bytes(),
            project.load_module_info(m).docstring,
        ) for m in data)
        cursor.executemany("""
            INSERT INTO module (name, content, docstring) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING
        """, values)

    def load_symbol(module: LeanName):
        symbols = [s for s in project.load_info(module, Symbol) if not is_internal(s.name)]
        values = ((
            Jsonb(s.name),
            Jsonb(module),
            s.type,
            s.is_prop,
        ) for s in symbols)
        cursor.executemany("""
            INSERT INTO symbol (name, module_name, type, is_prop) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING
        """, values)
        for s in symbols:
            values = ({
                "source": Jsonb(s.name),
                "target": Jsonb(t),
            } for t in s.type_references if not is_internal(t))
            cursor.executemany("""
                INSERT INTO dependency (source, target, on_type)
                    SELECT %(source)s, %(target)s, TRUE
                    WHERE EXISTS(SELECT 1 FROM symbol WHERE name = %(target)s)
                ON CONFLICT DO NOTHING
            """, values)

            if s.value_references is not None:
                values = ({
                    "source": Jsonb(s.name),
                    "target": Jsonb(t),
                } for t in s.value_references if not is_internal(t))
                cursor.executemany("""
                    INSERT INTO dependency (source, target, on_type)
                        SELECT %(source)s, %(target)s, FALSE
                        WHERE EXISTS(SELECT 1 FROM symbol WHERE name = %(target)s)
                    ON CONFLICT DO NOTHING
                """, values)

    def load_declaration(module: LeanName):
        declarations = project.load_info(module, Declaration)
        cursor.execute("""
            SELECT content FROM module WHERE name = %s
        """, (Jsonb(module),))
        source, = cursor.fetchone()
        values = ((
            Jsonb(module),
            i,
            Jsonb(d.name) if d.kind != "example" else None,
            d.modifiers.visibility != "private" and d.kind != "example",
            d.modifiers.docstring,
            d.kind,
            d.signature.pp if d.signature.pp is not None else source[d.signature.range.as_slice()].decode(),
            source[d.value.range.as_slice()].decode() if d.value is not None else None,
        ) for i, d in enumerate(declarations) if not is_internal(d.name))
        cursor.executemany("""
            INSERT INTO declaration (module_name, index, name, visible, docstring, kind, signature, value)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING 
        """, values)

    def topological_sort():
        logger.info("performing topological sort")
        cursor.execute("""
            INSERT INTO level (symbol_name, level)
                SELECT name, 0
                FROM symbol v
                WHERE NOT EXISTS (SELECT 1 FROM dependency e WHERE e.source = v.name)
        """)
        while cursor.rowcount:
            logger.info("topological sort: %d rows affected", cursor.rowcount)
            # Find all nodes whose direct predecessors have already been assigned a level
            cursor.execute("""
                INSERT INTO level (symbol_name, level)
                    SELECT e.source AS symbol_name, MAX(l.level) + 1 AS level
                    FROM
                        dependency e LEFT JOIN level l ON e.target = l.symbol_name
                    WHERE NOT EXISTS(SELECT 1 FROM level l WHERE l.symbol_name = e.source)
                    GROUP BY e.source
                    HAVING
                        EVERY(l.level IS NOT NULL) = TRUE
            """)

    create_table(cursor)
    lean_sysroot = Path(os.environ["LEAN_SYSROOT"])
    lean_src = lean_sysroot / "src" / "lean"
    all_modules = []
    for d in project.root, lean_src:
        results = project.batch_run_jixia(
            base_dir=d,
            prefixes=prefixes,
            plugins=["module", "declaration", "symbol"],
        )
        modules = [r[0] for r in results]
        load_module(modules, d)
        all_modules += modules

    for m in all_modules:
        load_symbol(m)
        load_declaration(m)
    topological_sort()
