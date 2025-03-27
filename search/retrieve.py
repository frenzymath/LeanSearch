import os

import chromadb
from jixia.structs import LeanName, DeclarationKind, parse_name
from psycopg import Connection
from psycopg.types.json import Jsonb
from pydantic.dataclasses import dataclass

from database.embedding import MistralEmbedding


@dataclass
class QueryResult:
    module: LeanName
    kind: DeclarationKind
    name: LeanName
    signature: str
    value: str | None
    docstring: str | None
    informal_name: str
    informal_description: str
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
        with self.conn.cursor() as cursor:
            for ids, distances in zip(results["ids"], results["distances"]):
                current_results = []
                for doc_id, distance in zip(ids, distances):
                    module_name, _, index = doc_id.partition(":")
                    module_name = parse_name(module_name)
                    cursor.execute("""
                        SELECT d.kind, d.name, d.signature, d.value, d.docstring, i.name, i.description
                        FROM declaration d INNER JOIN informal i ON d.name = i.symbol_name
                        WHERE d.module_name = %s AND d.index = %s
                    """, (Jsonb(module_name), index))
                    data = cursor.fetchone()
                    current_results.append(QueryResult(module_name, *data, distance))
            ret.append(current_results)
        return ret
