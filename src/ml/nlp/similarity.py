"""src/ml/nlp/similarity.py — SBERT-based plagiarism detection."""
from __future__ import annotations

from functools import lru_cache

import numpy as np

from src.core.settings import settings


@lru_cache(maxsize=1)
def get_sbert_model():
    """Load SBERT once. all-MiniLM-L6-v2 = 90MB, fast on CPU."""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(settings.sbert_model)


def compute_text_similarity(text_a: str, text_b: str) -> float:
    """Cosine similarity between two text answers (0–1)."""
    model = get_sbert_model()
    embs = model.encode([text_a, text_b], normalize_embeddings=True)
    return float(max(0.0, min(1.0, np.dot(embs[0], embs[1]))))


def batch_similarity_check(
    student_answers: dict[str, str],
    threshold: float | None = None,
) -> list[dict]:
    """
    Check all pairs for similarity. Returns flagged pairs.
    student_answers: {student_id: answer_text}
    """
    if threshold is None:
        threshold = settings.similarity_threshold
    if len(student_answers) < 2:
        return []

    model = get_sbert_model()
    ids = list(student_answers.keys())
    texts = [student_answers[sid] for sid in ids]
    embs = model.encode(texts, normalize_embeddings=True, batch_size=32)
    sim_matrix = embs @ embs.T

    flagged = []
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            sim = float(sim_matrix[i, j])
            if sim >= threshold:
                flagged.append({
                    "student_a": ids[i],
                    "student_b": ids[j],
                    "similarity": round(sim, 4),
                })
    return sorted(flagged, key=lambda x: x["similarity"], reverse=True)