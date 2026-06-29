from typing import List, Dict, Any

import numpy as np
import torch
from sentence_transformers import CrossEncoder


class Reranker:
    """
    Cross-encoder reranker (BAAI/bge-reranker-v2-m3).

    Stage 1 vector search is fast but shallow; this cross-encoder reads the query
    and each candidate chunk together to score true relevance. Scores are passed
    through a sigmoid so they fall in [0, 1] and can be threshold-gated.
    """

    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3"):
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Loading reranker model: {self.model_name} on device: {self.device}")
        self.model = CrossEncoder(self.model_name, device=self.device)

    def rerank(self, query: str, documents: List[str], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Scores each document against the query and returns the top_k, sorted by
        descending relevance.

        Returns a list of dicts: {"index", "document", "score"}, where "index"
        is the document's position in the input list (so callers can realign
        metadata / sources).
        """
        if not documents:
            return []

        pairs = [(query, doc) for doc in documents]
        raw_scores = np.array(self.model.predict(pairs))
        # bge-reranker-v2-m3 emits raw logits; sigmoid maps them to [0, 1].
        scores = 1.0 / (1.0 + np.exp(-raw_scores))

        ranked = sorted(
            ({"index": i, "document": documents[i], "score": float(scores[i])} for i in range(len(documents))),
            key=lambda r: r["score"],
            reverse=True,
        )
        return ranked[:top_k]
