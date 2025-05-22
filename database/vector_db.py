import os
import logging

import chromadb
from chromadb.api.types import Metadata, ID, Embedding, Document
from jixia.structs import pp_name
from psycopg import Connection

from .embedding import MistralEmbedding

logger = logging.getLogger(__name__)

def create_vector_db(conn: Connection, path: str, batch_size: int, project_name: str):
    with open("prompt/embedding_instruction.txt") as fp:
        instruction = fp.read()
    MistralEmbedding.setup_env()
    embedding = MistralEmbedding(os.environ["EMBEDDING_DEVICE"], instruction)

    client = chromadb.PersistentClient(path)
    collection = client.create_collection(
        name="leansearch",
        metadata={"hnsw:space": "cosine"},
        embedding_function=None,
    )

    with conn.cursor() as cursor:
        cursor.execute(
            """
                SELECT d.module_name, d.index, d.kind, d.name, d.signature, i.name, i.description, m.project_name
                FROM
                    declaration d
                    INNER JOIN informal i ON d.name = i.symbol_name
                    INNER JOIN module m ON d.module_name = m.name
                WHERE d.visible = TRUE AND m.project_name = %(project_name)s
            """,
            {
                "project_name": project_name
            }
        )

        while batch := cursor.fetchmany(batch_size):
            batch_doc: list[Document] = []
            batch_id: list[ID] = []
            metadatas: list[Metadata] = []
            for module_name, index, kind, name, signature, informal_name, informal_description, this_row_project_name in batch:
                batch_doc.append(f"{kind} {name} {signature}\n{informal_name}: {informal_description}")
                # NOTE: we use module name + index as document id as they cannot contain special characters
                batch_id.append(f"{pp_name(module_name)}:{index}")
                metadatas.append({ "project_name": this_row_project_name })
                if os.environ["DRY_RUN"] == "true":
                    logger.info("DRY_RUN:skipped embedding: %s", f"{kind} {name} {signature} {informal_name}")
            if os.environ["DRY_RUN"] == "true":
                return
            batch_embedding : list[Embedding] = embedding.embed(batch_doc)
            collection.add(embeddings=batch_embedding, ids=batch_id, metadatas=metadatas)
