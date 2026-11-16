"""Day 6 embedding model, reused unchanged so query vectors stay compatible with the Day 6 index.

BAAI/bge-m3 dense, pinned revision, local via sentence-transformers; 1024 dims; L2-normalized
(cosine in pgvector == 1 - dot); no instruction prefix for queries. No fallback: a load error stops the run.
"""
from __future__ import annotations

import os

DEFAULT_MODEL = "BAAI/bge-m3"
DEFAULT_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"


class BgeM3Embedder:
    def __init__(self, model_name: str | None = None, revision: str | None = None, device: str | None = None,
                 max_seq_length: int = 2048, batch_size: int = 8) -> None:
        import torch
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name or os.getenv("EMBEDDING_MODEL") or DEFAULT_MODEL
        self.revision = revision or os.getenv("EMBEDDING_REVISION") or DEFAULT_REVISION
        self.device = device or ("mps" if torch.backends.mps.is_available() else "cpu")
        self.batch_size, self.max_seq_length = batch_size, max_seq_length
        self.model = SentenceTransformer(self.model_name, revision=self.revision, device=self.device)
        self.model.max_seq_length = max_seq_length
        get_dim = getattr(self.model, "get_embedding_dimension", None) or self.model.get_sentence_embedding_dimension
        self.dimensions = get_dim()

    @property
    def key(self) -> str:
        """Identifier stored with every vector: model@revision[:12]."""
        return f"{self.model_name}@{self.revision[:12]}"

    def _encode(self, texts: list[str]) -> list[list[float]]:
        v = self.model.encode(texts, batch_size=self.batch_size, normalize_embeddings=True,
                              convert_to_numpy=True, show_progress_bar=False)
        if v.shape[1] != self.dimensions:
            raise RuntimeError(f"expected {self.dimensions} dims, got {v.shape[1]}")
        return v.tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._encode(texts) if texts else []

    def embed_query(self, question: str) -> list[float]:
        return self._encode([question])[0]
