import logging

import requests
from chromadb import Documents, Embeddings

logger = logging.getLogger(__name__)

# For a reference, see https://huggingface.co/intfloat/e5-mistral-7b-instruct

DIMENSION = 4096
MAX_LENGTH = 4096


class MistralEmbedding:
    def __init__(self, url: str, instruction: str):
        self.instruction = instruction
        self.url = url

    def get_detailed_instruct(self, query: str) -> str:
        return f"Instruct: {self.instruction}\nDoc: {query}"

    def embed(self, docs: Documents) -> Embeddings:
        detailed_docs = [self.get_detailed_instruct(doc[:MAX_LENGTH]) for doc in docs]
        response = requests.post(self.url, json=detailed_docs)
        return response.json()
