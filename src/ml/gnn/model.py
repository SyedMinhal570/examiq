"""src/ml/gnn/model.py — GNN-based collusion detector."""
from __future__ import annotations

import numpy as np

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch_geometric.nn import GCNConv
    _TORCH_AVAILABLE = True
except ImportError:
    _TORCH_AVAILABLE = False


class CollusionGNN(nn.Module if _TORCH_AVAILABLE else object):  # type: ignore
    """2-layer GCN for binary collusion classification."""

    def __init__(self, input_dim: int = 64, hidden_dim: int = 128):
        if not _TORCH_AVAILABLE:
            raise ImportError("torch and torch-geometric required for GNN")
        super().__init__()
        self.conv1 = GCNConv(input_dim, hidden_dim)
        self.conv2 = GCNConv(hidden_dim, hidden_dim // 2)
        self.bn1 = nn.BatchNorm1d(hidden_dim)
        self.bn2 = nn.BatchNorm1d(hidden_dim // 2)
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim // 2, 32),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(32, 2),
        )

    def forward(self, x, edge_index):
        x = F.dropout(F.relu(self.bn1(self.conv1(x, edge_index))), p=0.3, training=self.training)
        x = F.relu(self.bn2(self.conv2(x, edge_index)))
        return self.classifier(x)


class CollusionDetector:
    """
    High-level interface. Falls back to cosine heuristic if GNN model not found.
    """

    def __init__(self, model_path: str | None = None):
        self.model = None
        if _TORCH_AVAILABLE and model_path:
            try:
                import torch
                m = CollusionGNN()
                m.load_state_dict(torch.load(model_path, map_location="cpu"))
                m.eval()
                self.model = m
            except Exception:
                pass  # Use heuristic fallback

    def detect_collusion(
        self,
        student_ids: list[str],
        answer_vectors: list[list[float]],
        threshold: float = 0.85,
    ) -> dict[str, float]:
        n = len(student_ids)
        if n < 2:
            return {sid: 0.0 for sid in student_ids}

        vectors = np.array(answer_vectors, dtype=np.float32)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        normalized = vectors / norms
        sim_matrix = normalized @ normalized.T

        if self.model is not None and _TORCH_AVAILABLE:
            return self._gnn_detect(student_ids, vectors, sim_matrix, threshold)
        return self._heuristic_detect(student_ids, sim_matrix)

    def _heuristic_detect(self, student_ids, sim_matrix) -> dict[str, float]:
        """Simple max-similarity heuristic when GNN model not available."""
        n = len(student_ids)
        probs = {}
        for i, sid in enumerate(student_ids):
            sims = [sim_matrix[i, j] for j in range(n) if i != j]
            probs[sid] = float(max(sims)) if sims else 0.0
        return probs

    def _gnn_detect(self, student_ids, vectors, sim_matrix, threshold) -> dict[str, float]:
        import torch
        n = len(student_ids)
        feat_dim = 64
        padded = np.zeros((n, feat_dim), dtype=np.float32)
        cols = min(vectors.shape[1], feat_dim)
        padded[:, :cols] = vectors[:, :cols]

        edges_src, edges_dst = [], []
        for i in range(n):
            for j in range(i + 1, n):
                if sim_matrix[i, j] >= threshold:
                    edges_src.extend([i, j])
                    edges_dst.extend([j, i])

        x = torch.tensor(padded)
        edge_index = (
            torch.tensor([edges_src, edges_dst], dtype=torch.long)
            if edges_src else torch.zeros((2, 0), dtype=torch.long)
        )
        with torch.no_grad():
            logits = self.model(x, edge_index)
            probs = torch.softmax(logits, dim=1)[:, 1].numpy()
        return {sid: float(p) for sid, p in zip(student_ids, probs)}