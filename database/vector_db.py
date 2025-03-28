import os

import chromadb
import torch.cuda
from jixia.structs import pp_name
from psycopg import Connection

from .embedding import MistralEmbedding


def create_vector_db(conn: Connection, path: str, batch_size: int):
    with open("prompt/embedding_instruction.txt") as fp:
        instruction = fp.read()
    MistralEmbedding.setup_env()
    try:
        device = os.environ["EMBEDDING_DEVICE"]
    except KeyError:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    embedding = MistralEmbedding(device, instruction)

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

        batch_doc = []
        batch_id = []
        while batch := cursor.fetchmany(batch_size):
            batch_doc.clear()
            batch_id.clear()
            for module_name, index, kind, name, signature, informal_name, informal_description in batch:
                # NOTE: we use module name + index as document id as they cannot contain special characters
                doc = f"{kind} {name} {signature}\n{informal_name}: {informal_description}"
                batch_doc.append(doc)
                doc_id = f"{pp_name(module_name)}:{index}"
                batch_id.append(doc_id)
            batch_embedding = embedding.embed(batch_doc)
            collection.add(embeddings=batch_embedding, ids=batch_id)
