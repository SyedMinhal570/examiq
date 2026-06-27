"""
src/ml/irt/model.py
────────────────────
3-Parameter Logistic Item Response Theory implementation.
Pure NumPy — no ML framework needed. Fast on CPU.
"""
from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from scipy.optimize import minimize_scalar
from scipy.special import expit
from scipy.stats import norm


@dataclass
class IRTItem:
    item_id: str
    a: float = 1.0      # discrimination  (0.5 – 2.5)
    b: float = 0.0      # difficulty      (-3.0 – 3.0)
    c: float = 0.25     # guessing        (0.0 – 0.35)
    content: str = ""
    options: list[str] = field(default_factory=list)
    correct_option: int = 0


class IRTModel:
    """3PL IRT: ability estimation, item information, adaptive selection."""

    @staticmethod
    def probability(theta: float, a: float, b: float, c: float) -> float:
        """P(correct | θ) using 3PL logistic model."""
        return c + (1 - c) * float(expit(a * (theta - b)))

    @staticmethod
    def fisher_information(theta: float, a: float, b: float, c: float) -> float:
        """Fisher Information at θ for item (a, b, c). Higher = more informative."""
        p = IRTModel.probability(theta, a, b, c)
        q = 1 - p
        if p <= c or q < 1e-9:
            return 0.0
        return (a ** 2 * q * ((p - c) / (1 - c)) ** 2) / p

    @staticmethod
    def estimate_theta_mle(
        responses: list[tuple[IRTItem, int]],
        theta_range: tuple[float, float] = (-4.0, 4.0),
    ) -> tuple[float, float]:
        """
        MLE estimate of θ from response history.
        Returns (theta_hat, standard_error).
        """
        if not responses:
            return 0.0, 999.0

        def neg_log_likelihood(theta: float) -> float:
            nll = 0.0
            for item, resp in responses:
                p = IRTModel.probability(theta, item.a, item.b, item.c)
                p = np.clip(p, 1e-9, 1 - 1e-9)
                nll -= np.log(p) if resp == 1 else np.log(1 - p)
            return nll

        result = minimize_scalar(neg_log_likelihood, bounds=theta_range, method="bounded")
        theta_hat = float(result.x)
        total_info = sum(
            IRTModel.fisher_information(theta_hat, item.a, item.b, item.c)
            for item, _ in responses
        )
        se = 1.0 / np.sqrt(max(total_info, 1e-9))
        return theta_hat, se

    @staticmethod
    def select_next_item(
        theta: float,
        available_items: list[IRTItem],
        administered_ids: set[str],
    ) -> IRTItem | None:
        """Select item with maximum Fisher Information at current θ."""
        candidates = [i for i in available_items if i.item_id not in administered_ids]
        if not candidates:
            return None
        return max(
            candidates,
            key=lambda item: IRTModel.fisher_information(theta, item.a, item.b, item.c)
        )

    @staticmethod
    def theta_to_percentile(theta: float) -> int:
        return int(norm.cdf(theta) * 100)

    @staticmethod
    def theta_to_grade(theta: float) -> str:
        if theta >= 2.0:  return "A+"
        if theta >= 1.5:  return "A"
        if theta >= 1.0:  return "A-"
        if theta >= 0.5:  return "B+"
        if theta >= 0.0:  return "B"
        if theta >= -0.5: return "B-"
        if theta >= -1.0: return "C+"
        if theta >= -1.5: return "C"
        return "F"