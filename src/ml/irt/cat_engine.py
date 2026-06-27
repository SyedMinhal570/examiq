"""src/ml/irt/cat_engine.py — CAT Session state management."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.core.settings import settings
from src.ml.irt.model import IRTItem, IRTModel


@dataclass
class CATSession:
    session_id: str
    student_id: str
    exam_id: str
    theta: float = 0.0
    theta_se: float = 999.0
    responses: list[dict] = field(default_factory=list)
    administered_ids: list[str] = field(default_factory=list)
    item_times: list[float] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = "active"

    @property
    def items_administered(self) -> int:
        return len(self.responses)

    @property
    def should_stop(self) -> bool:
        if self.items_administered < settings.min_items_before_estimate:
            return False
        if self.items_administered >= settings.max_items_per_exam:
            return True
        return self.theta_se < settings.theta_convergence_threshold

    def record_response(self, item: IRTItem, correct: bool, time_taken: float) -> None:
        self.responses.append({
            "item_id": item.item_id,
            "correct": correct,
            "a": item.a, "b": item.b, "c": item.c,
        })
        self.administered_ids.append(item.item_id)
        self.item_times.append(time_taken)

        # Update theta estimate
        item_responses = [
            (IRTItem(r["item_id"], r["a"], r["b"], r["c"]), 1 if r["correct"] else 0)
            for r in self.responses
        ]
        self.theta, self.theta_se = IRTModel.estimate_theta_mle(item_responses)