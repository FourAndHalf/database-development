import os
from typing import List, Dict, Any

import numpy as np
from sentence_transformers import CrossEncoder


class Reranker:
    """
    Cross-encoder reranker (BAAI/bge-reranker-v2-m3).

    Stage 1 vector search is fast but shallow; this cross-encoder reads the query
    and each candidate chunk together to score true relevance. Scores are passed
    through a sigmoid so they fall in [0, 1] and can be threshold-gated.

    Defaults to CPU: the embedder (bge-m3) already occupies the GPU, and scoring a
    small candidate pool on CPU is cheap. Override with RERANKER_DEVICE=cuda.
    """

    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3"):
        self.model_name = model_name
        self.device = os.getenv("RERANKER_DEVICE", "cpu")
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
        # CrossEncoder.predict already applies sigmoid for this model, so scores
        # are in [0, 1] — do not sigmoid again or the range collapses to [0.5, 1].
        scores = np.array(self.model.predict(pairs))

        ranked = sorted(
            ({"index": i, "document": documents[i], "score": float(scores[i])} for i in range(len(documents))),
            key=lambda r: r["score"],
            reverse=True,
        )
        return ranked[:top_k]
