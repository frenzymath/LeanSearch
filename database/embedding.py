import logging
import os

import numpy as np
import requests
import torch
from chromadb import Documents, Embeddings
from torch import Tensor
from transformers import AutoTokenizer, AutoModel

logger = logging.getLogger(__name__)

# For a reference, see https://huggingface.co/intfloat/e5-mistral-7b-instruct

DIMENSION = 4096
MAX_LENGTH = 4096


def last_token_pool(last_hidden_states: Tensor, attention_mask: Tensor) -> Tensor:
    left_padding = attention_mask[:, -1].sum() == attention_mask.shape[0]
    if left_padding:
        return last_hidden_states[:, -1]
    else:
        sequence_lengths = attention_mask.sum(dim=1) - 1
        batch_size = last_hidden_states.shape[0]
        return last_hidden_states[torch.arange(batch_size, device=last_hidden_states.device), sequence_lengths]


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
