from typing import LiteralString
from psycopg import Connection


def create_schema(conn: Connection):
    sql: list[LiteralString] = [
        """
        CREATE TABLE module (
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
        CREATE TABLE symbol (
            name JSONB PRIMARY KEY,
            module_name JSONB REFERENCES module(name) NOT NULL,
            type TEXT NOT NULL,
            is_prop BOOLEAN NOT NULL
        )
        """,
        """
        CREATE TABLE declaration (
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
        CREATE TABLE dependency (
            source JSONB REFERENCES symbol(name) NOT NULL,
            target JSONB REFERENCES symbol(name) NOT NULL,
            on_type BOOLEAN NOT NULL,
            PRIMARY KEY (source, target, on_type)
        )
        """,
        """
        CREATE TABLE level (
            symbol_name JSONB PRIMARY KEY REFERENCES symbol(name) NOT NULL,
            level INTEGER NOT NULL
        )
        """,
        """
        CREATE TABLE informal (
            symbol_name JSONB PRIMARY KEY REFERENCES symbol(name) NOT NULL,
            name TEXT NOT NULL,
            description TEXT NOT NULL
        )
        """,
        """
        CREATE VIEW record AS
        SELECT
            d.module_name, d.index, d.kind, d.name, d.signature, s.type, d.value, d.docstring,
            i.name AS informal_name, i.description AS informal_description
        FROM
            declaration d
            INNER JOIN informal i ON d.name = i.symbol_name
            INNER JOIN symbol s ON d.name = s.name
        """,
    ]

    with conn.cursor() as cursor:
        for s in sql:
            cursor.execute(s)
