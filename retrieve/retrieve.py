import os

import chromadb
from jixia.structs import LeanName, DeclarationKind, parse_name
from psycopg import Connection
from psycopg.rows import class_row
from psycopg.types.json import Jsonb
from pydantic import BaseModel

from database.embedding import MistralEmbedding


class Record(BaseModel):
    module_name: LeanName
    kind: DeclarationKind
    name: LeanName
    signature: str
    type: str
    value: str | None
    docstring: str | None
    informal_name: str
    informal_description: str


class QueryResult(BaseModel):
    result: Record
    distance: float


class Retriever:
    def __init__(self, path: str, conn: Connection):
        self.conn = conn
        self.client = chromadb.PersistentClient(path)
        self.collection = self.client.get_collection(name="leansearch", embedding_function=None)
        with open("prompt/retrieve_instruction.txt") as fp:
            instruction = fp.read()
        self.embedding = MistralEmbedding(os.environ.get("EMBEDDING_DEVICE", "cpu"), instruction)

    def batch_search(self, query: list[str], num_results: int) -> list[list[QueryResult]]:
        query_embedding = self.embedding.embed(query)
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=num_results,
            include=["distances"],
        )
        ret = []
        with self.conn.cursor(row_factory=class_row(Record)) as cursor:
            for ids, distances in zip(results["ids"], results["distances"]):
                current_results = []
                for doc_id, distance in zip(ids, distances):
                    module_name, _, index = doc_id.partition(":")
                    module_name = parse_name(module_name)
                    cursor.execute("""
                        SELECT
                            d.module_name, d.kind, d.name, d.signature, s.type, d.value, d.docstring,
                            i.name AS informal_name, i.description AS informal_description
                        FROM
                            declaration d
                            INNER JOIN informal i ON d.name = i.symbol_name
                            INNER JOIN symbol s ON d.name = s.name
                        WHERE d.module_name = %s AND d.index = %s
                    """, (Jsonb(module_name), index))
                    result = cursor.fetchone()
                    current_results.append(QueryResult(result=result, distance=distance))
                ret.append(current_results)
        return ret
