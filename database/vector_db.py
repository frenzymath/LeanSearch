import os
import logging

import chromadb
from jixia.structs import pp_name
from psycopg import Connection

from .embedding import MistralEmbedding

logger = logging.getLogger(__name__)

def create_vector_db(conn: Connection, path: str, batch_size: int):
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
        cursor.execute("""
            SELECT d.module_name, d.index, d.kind, d.name, d.signature, i.name, i.description
            FROM
                declaration d INNER JOIN informal i ON d.name = i.symbol_name
            WHERE d.visible = TRUE
        """)

        while batch := cursor.fetchmany(batch_size):
            batch_doc = []
            batch_id = []
            for module_name, index, kind, name, signature, informal_name, informal_description in batch:
                batch_doc.append(f"{kind} {name} {signature}\n{informal_name}: {informal_description}")
                # NOTE: we use module name + index as document id as they cannot contain special characters
                batch_id.append(f"{pp_name(module_name)}:{index}")
                if os.environ["DRY_RUN"] == "true":
                    logger.info("DRY_RUN:skipped embedding: %s", f"{kind} {name} {signature} {informal_name}")
            if os.environ["DRY_RUN"] == "true":
                return
            batch_embedding = embedding.embed(batch_doc)
            collection.add(embeddings=batch_embedding, ids=batch_id)
