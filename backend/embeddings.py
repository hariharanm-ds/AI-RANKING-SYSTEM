"""Embedding generation and FAISS similarity search."""

import hashlib
from typing import Any

import numpy as np

try:
    import faiss
    from sentence_transformers import SentenceTransformer
except ImportError:
    faiss = None
    SentenceTransformer = None


class EmbeddingIndex:
    """Manages SentenceTransformer embeddings and a FAISS index."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self.model = SentenceTransformer(model_name) if SentenceTransformer else None
        self.dimension = (
            self.model.get_sentence_embedding_dimension()
            if self.model
            else 384
        )
        self.index: Any | None = None
        self.vectors: np.ndarray | None = None
        self.documents: list[str] = []
        self.metadata: list[dict[str, Any]] = []

    def _normalize(self, vectors: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return vectors / norms

    def encode(self, texts: list[str]) -> np.ndarray:
        if self.model:
            embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
            return self._normalize(embeddings.astype("float32"))

        embeddings = np.zeros((len(texts), self.dimension), dtype="float32")
        for row, text in enumerate(texts):
            for token in text.lower().split():
                digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
                bucket = int.from_bytes(digest[:4], "little") % self.dimension
                sign = 1.0 if digest[4] % 2 == 0 else -1.0
                embeddings[row, bucket] += sign
        return self._normalize(embeddings.astype("float32"))

    def build(self, documents: list[str], metadata: list[dict[str, Any]]) -> None:
        if not documents:
            raise ValueError("No documents provided for embedding index.")
        if len(documents) != len(metadata):
            raise ValueError("Documents and metadata length mismatch.")

        self.documents = documents
        self.metadata = metadata
        vectors = self.encode(documents)
        if faiss:
            self.index = faiss.IndexFlatIP(self.dimension)
            self.index.add(vectors)
        else:
            self.vectors = vectors

    def search(self, query: str, top_k: int | None = None) -> list[dict[str, Any]]:
        if (self.index is None and self.vectors is None) or not self.documents:
            raise ValueError("Embedding index has not been built.")

        k = top_k or len(self.documents)
        k = min(k, len(self.documents))

        query_vector = self.encode([query])
        if self.index is not None:
            scores, indices = self.index.search(query_vector, k)
            score_row = scores[0]
            index_row = indices[0]
        else:
            similarities = np.dot(self.vectors, query_vector[0])
            index_row = np.argsort(similarities)[::-1][:k]
            score_row = similarities[index_row]

        results: list[dict[str, Any]] = []
        for score, idx in zip(score_row, index_row):
            if idx < 0:
                continue
            results.append(
                {
                    "index": int(idx),
                    "similarity_score": float(score),
                    "document": self.documents[idx],
                    "metadata": self.metadata[idx],
                }
            )
        return results
