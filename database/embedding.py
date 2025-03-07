import logging
import os

import numpy as np
import torch
from chromadb import Documents, Embeddings
from torch import Tensor
from transformers import AutoTokenizer, AutoModel

logger = logging.getLogger(__name__)

# For a reference, see https://huggingface.co/intfloat/e5-mistral-7b-instruct

DIMENSION = 4096
MAX_LENGTH = 4096


def last_token_pool(last_hidden_states: Tensor, attention_mask: Tensor) -> Tensor:
    left_padding = (attention_mask[:, -1].sum() == attention_mask.shape[0])
    if left_padding:
        return last_hidden_states[:, -1]
    else:
        sequence_lengths = attention_mask.sum(dim=1) - 1
        batch_size = last_hidden_states.shape[0]
        return last_hidden_states[torch.arange(batch_size, device=last_hidden_states.device), sequence_lengths]


class MistralEmbedding:
    def __init__(self, device: str, instruction: str):
        self.device = torch.device(device)
        logger.info(f"use device %s for embedding", self.device)
        self.tokenizer = AutoTokenizer.from_pretrained("intfloat/e5-mistral-7b-instruct")
        self.model = AutoModel.from_pretrained(
            "intfloat/e5-mistral-7b-instruct",
            torch_dtype=torch.float16,
        ).to(self.device)
        self.model.eval()
        self.instruction = instruction

    def get_detailed_instruct(self, query: str) -> str:
        return f"Instruct: {self.instruction}\nDoc: {query}"

    def embed(self, docs: Documents) -> Embeddings:
        with torch.no_grad():
            detailed_docs = [self.get_detailed_instruct(doc[:MAX_LENGTH]) for doc in docs]
            batch_dict = self.tokenizer(
                detailed_docs,
                max_length=MAX_LENGTH - 1,
                return_attention_mask=False,
                padding=False,
                truncation=True,
            )
            for input_ids in batch_dict["input_ids"]:
                input_ids.append(self.tokenizer.eos_token_id)
            batch_dict = self.tokenizer.pad(
                batch_dict,
                padding=True,
                return_attention_mask=True,
                return_tensors='pt',
            ).to(self.device)
            torch.cuda.empty_cache()
            outputs = self.model(**batch_dict)
            embeddings = last_token_pool(outputs.last_hidden_state, batch_dict['attention_mask'])
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
            return embeddings.cpu().numpy().astype(np.float32).reshape(-1, DIMENSION).tolist()

    @staticmethod
    def setup_env():
        os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:32"
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
