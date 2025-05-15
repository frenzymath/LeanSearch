import logging
import os
from collections.abc import Iterable
from pathlib import Path

from jixia import LeanProject
from jixia.structs import LeanName, Symbol, Declaration, is_internal
from psycopg import Connection
from psycopg.types.json import Jsonb

logger = logging.getLogger(__name__)

def _get_signature(declaration: Declaration, module_content):
    if declaration.signature.pp is not None:
        return declaration.signature.pp
    elif declaration.signature.range is not None:
        return module_content[declaration.signature.range.as_slice()].decode()
    else:
        return ''

def _get_value(declaration: Declaration, module_content):
    if declaration.value is not None and declaration.value.range is not None:
        return module_content[declaration.value.range.as_slice()].decode()
    else:
        return None

def _find_declaration(declarations: list[Declaration], target_name):
    for index, declaration in enumerate(declarations):
        if declaration.name == target_name:
            return declaration, index
    return None, None

def load_data(project: LeanProject, prefixes: list[LeanName], conn: Connection):
    def load_module(module_names: Iterable[LeanName], base_dir: Path):
        for module_name in module_names:
            db_module = {
                "name": Jsonb(module_name),
                "content": project.path_of_module(module_name, base_dir).read_bytes(),
                "docstring": project.load_module_info(module_name).docstring
            }
            cursor.execute(
                """
                INSERT INTO module (name, content, docstring) VALUES (%(name)s, %(content)s, %(docstring)s)
                """,
                db_module
            )

            symbols = project.load_info(module_name, Symbol)
            declarations = project.load_info(module_name, Declaration)
            for symbol in symbols:
                declaration, index = _find_declaration(declarations, symbol.name)
                if (
                    is_internal(symbol.name) or
                    declaration is None or
                    declaration.kind == "proofWanted"
                ):
                    continue

                cursor.execute(
                    """
                    INSERT INTO declaration (module_name, index, name, visible, docstring, kind, signature, value, symbol_type, symbol_is_prop)
                    VALUES (%(module_name)s, %(index)s, %(name)s, %(visible)s, %(docstring)s, %(kind)s, %(signature)s, %(value)s, %(symbol_type)s, %(symbol_is_prop)s)
                    """,
                    {
                        "module_name": Jsonb(module_name),
                        "name"       : Jsonb(declaration.name) if declaration.kind != "example" else None,
                        "index"      : index,
                        "visible"    : declaration.modifiers.visibility != "private" and declaration.kind != "example",
                        "docstring"  : declaration.modifiers.docstring,
                        "kind"       : declaration.kind,
                        "signature"  : _get_signature(declaration, db_module["content"]),
                        "value"      : _get_value(declaration, db_module["content"]),
                        "symbol_type": symbol.type,
                        "symbol_is_prop": symbol.is_prop
                    }
                )

                db_deps = []
                for ref_name in symbol.type_references:
                    if is_internal(ref_name):
                        continue
                    db_deps.append({
                        "source": Jsonb(symbol.name),
                        "target": Jsonb(ref_name),
                        "on_type": True
                    })
                for ref_name in (symbol.value_references or []):
                    if is_internal(ref_name):
                        continue
                    db_deps.append({
                        "source": Jsonb(symbol.name),
                        "target": Jsonb(ref_name),
                        "on_type": False
                    })
                cursor.executemany(
                    """
                    INSERT INTO dependency (source, target, on_type)
                    VALUES (%(source)s, %(target)s, %(on_type)s)
                    """,
                    db_deps,
                )

    def topological_sort():
        logger.info("performing topological sort")
        # Delete dependencies where target doesn't exist in declaration table
        cursor.execute("""
            DELETE FROM dependency d
            WHERE NOT EXISTS (SELECT 1 FROM declaration dec WHERE dec.name = d.target)
        """)
        logger.info("Deleted %d invalid dependencies", cursor.rowcount)

        cursor.execute("""
            INSERT INTO level (symbol_name, level)
                SELECT name, 0
                FROM declaration v
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

    with conn.cursor() as cursor:
        path_to_project = project.root
        project_modules = [r[0] for r in project.batch_run_jixia(
            base_dir=path_to_project,
            prefixes=prefixes,
            plugins=["module", "declaration", "symbol"],
        )]
        load_module(project_modules, path_to_project)

        path_to_lean = Path(os.environ["LEAN_SYSROOT"]) / "src" / "lean"
        lean_modules = [r[0] for r in project.batch_run_jixia(
            base_dir=path_to_lean,
            prefixes=prefixes,
            plugins=["module", "declaration", "symbol"],
        )]
        load_module(lean_modules, path_to_lean)
        topological_sort()
