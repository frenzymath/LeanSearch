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
        CREATE TABLE declaration (
            module_name JSONB REFERENCES module(name) NOT NULL,
            name JSONB,

            index INTEGER NOT NULL,
            visible BOOLEAN NOT NULL,
            docstring TEXT,
            kind declaration_kind NOT NULL,
            signature TEXT NOT NULL,
            value TEXT,

            symbol_type TEXT NOT NULL,
            symbol_is_prop BOOLEAN NOT NULL,

            PRIMARY KEY (name)
        )
        """,
        """
        CREATE TABLE dependency (
            source JSONB NOT NULL,
            target JSONB NOT NULL,
            on_type BOOLEAN NOT NULL,
            PRIMARY KEY (source, target, on_type)
        )
        """,
        """
        CREATE TABLE level (
            symbol_name JSONB PRIMARY KEY REFERENCES declaration(name) NOT NULL,
            level INTEGER NOT NULL
        )
        """,
        """
        CREATE TABLE informal (
            symbol_name JSONB PRIMARY KEY REFERENCES declaration(name) NOT NULL,
            name TEXT NOT NULL,
            description TEXT NOT NULL
        )
        """,
        """
        CREATE VIEW record AS
        SELECT
            d.module_name, d.index, d.kind, d.name, d.signature, d.symbol_type, d.value, d.docstring,
            i.name AS informal_name, i.description AS informal_description
        FROM
            declaration d
            INNER JOIN informal i ON d.name = i.symbol_name
        """,
    ]

    with conn.cursor() as cursor:
        for s in sql:
            cursor.execute(s)
