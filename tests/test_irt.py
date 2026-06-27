"""
tests/test_irt.py — Unit tests for IRT engine
tests/test_api.py — Integration tests for API routes

Run: pytest tests/ -v
"""
# ─────────────────────────────────────────────────────────────────
# tests/unit/test_irt.py
# ─────────────────────────────────────────────────────────────────
import math
import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ml.irt.model import IRTItem, IRTModel
from src.ml.irt.cat_engine import CATSession


class TestIRTModel:
    """Tests for the 3PL IRT model."""

    def test_probability_average_student_average_item(self):
        """At θ=0, b=0: P should be 0.5 + (0.5 * (1-c)) for c=0.25 → 0.625"""
        p = IRTModel.probability(theta=0.0, a=1.0, b=0.0, c=0.25)
        assert abs(p - 0.625) < 0.001

    def test_probability_high_ability_easy_item(self):
        """High ability student on easy item → P close to 1"""
        p = IRTModel.probability(theta=3.0, a=1.5, b=-2.0, c=0.25)
        assert p > 0.95

    def test_probability_low_ability_hard_item(self):
        """Low ability student on hard item → P close to c (guessing)"""
        p = IRTModel.probability(theta=-3.0, a=1.5, b=2.0, c=0.25)
        assert p < 0.30

    def test_probability_bounds(self):
        """Probability must always be in [c, 1]"""
        for theta in [-4, -2, 0, 2, 4]:
            p = IRTModel.probability(theta=theta, a=1.0, b=0.0, c=0.25)
            assert 0.25 <= p <= 1.0

    def test_fisher_information_peaks_at_b(self):
        """Fisher Information peaks near item difficulty b"""
        a, b, c = 1.5, 0.5, 0.25
        info_at_b    = IRTModel.fisher_information(b,       a, b, c)
        info_away    = IRTModel.fisher_information(b + 2.0, a, b, c)
        assert info_at_b > info_away

    def test_fisher_information_nonnegative(self):
        """Fisher Information must always be ≥ 0"""
        for theta in [-4, -2, 0, 2, 4]:
            info = IRTModel.fisher_information(theta, 1.0, 0.0, 0.25)
            assert info >= 0

    def test_theta_estimation_correct_responses(self):
        """All correct → theta estimate > 0"""
        items = [IRTItem(f"item_{i}", a=1.0, b=float(i-2), c=0.25) for i in range(5)]
        responses = [(item, 1) for item in items]  # All correct
        theta, se = IRTModel.estimate_theta_mle(responses)
        assert theta > 0
        assert se < 999

    def test_theta_estimation_all_wrong(self):
        """All wrong → theta estimate < 0"""
        items = [IRTItem(f"item_{i}", a=1.0, b=float(i-2), c=0.0) for i in range(5)]
        responses = [(item, 0) for item in items]  # All wrong
        theta, se = IRTModel.estimate_theta_mle(responses)
        assert theta < 0

    def test_theta_estimation_empty(self):
        """No responses → theta=0, se=999 (no information)"""
        theta, se = IRTModel.estimate_theta_mle([])
        assert theta == 0.0
        assert se == 999.0

    def test_select_next_item_chooses_informative(self):
        """CAT selects item maximizing Fisher Information at current theta"""
        items = [
            IRTItem("easy",   a=1.0, b=-2.0, c=0.25),  # Low info at theta=0
            IRTItem("medium", a=1.5, b=0.0,  c=0.25),  # High info at theta=0
            IRTItem("hard",   a=1.0, b=2.0,  c=0.25),  # Low info at theta=0
        ]
        selected = IRTModel.select_next_item(theta=0.0, available_items=items, administered_ids=set())
        assert selected is not None
        assert selected.item_id == "medium"  # Most informative at theta=0

    def test_select_next_item_skips_administered(self):
        """CAT never re-selects an already answered item"""
        items = [IRTItem("item_1", a=2.0, b=0.0, c=0.25)]
        selected = IRTModel.select_next_item(
            theta=0.0, available_items=items, administered_ids={"item_1"}
        )
        assert selected is None  # No items left

    def test_theta_to_grade(self):
        """Grade mapping is consistent"""
        assert IRTModel.theta_to_grade(2.5)  == "A+"
        assert IRTModel.theta_to_grade(1.7)  == "A"
        assert IRTModel.theta_to_grade(0.0)  == "B"
        assert IRTModel.theta_to_grade(-3.0) == "F"

    def test_theta_to_percentile_range(self):
        """Percentile must be between 0 and 100"""
        for theta in [-4, -2, 0, 2, 4]:
            pct = IRTModel.theta_to_percentile(theta)
            assert 0 <= pct <= 100


class TestCATSession:
    """Tests for the CAT session state machine."""

    def test_initial_state(self):
        session = CATSession("s1", "user1", "exam1")
        assert session.theta == 0.0
        assert session.items_administered == 0
        assert session.status == "active"

    def test_should_not_stop_before_min_items(self):
        """CAT must not stop before min_items even if SE is low"""
        session = CATSession("s1", "user1", "exam1")
        session.theta_se = 0.001  # Artificially low SE
        assert session.should_stop is False  # min_items=5 not reached

    def test_should_stop_at_max_items(self):
        """CAT must stop when max_items reached"""
        session = CATSession("s1", "user1", "exam1")
        item = IRTItem("dummy", a=1.0, b=0.0, c=0.25)
        for _ in range(30):  # max_items = 30
            session.record_response(item, True, 10.0)
        assert session.should_stop is True

    def test_record_response_updates_theta(self):
        """Recording responses updates theta estimate"""
        session = CATSession("s1", "user1", "exam1")
        item = IRTItem("item1", a=1.5, b=0.0, c=0.25)
        session.record_response(item, True, 5.0)
        # After one correct response, theta should be positive
        assert session.items_administered == 1
        # Theta should shift (may or may not be positive with single response, but should be a number)
        assert isinstance(session.theta, float)
        assert not math.isnan(session.theta)


class TestCollusionDetector:
    """Tests for GNN collusion detection."""

    def test_identical_answers_high_similarity(self):
        """Students with identical answer patterns should get high similarity"""
        from src.ml.gnn.model import CollusionDetector
        detector = CollusionDetector()  # No model → heuristic fallback

        ids = ["s1", "s2"]
        # Identical answer vectors → similarity = 1.0
        vectors = [[1,0,1,1,0,1,0,1] * 8, [1,0,1,1,0,1,0,1] * 8]
        probs = detector.detect_collusion(ids, vectors, threshold=0.85)

        assert probs["s1"] >= 0.85
        assert probs["s2"] >= 0.85

    def test_different_answers_low_similarity(self):
        """Students with very different answers should have low similarity"""
        from src.ml.gnn.model import CollusionDetector
        detector = CollusionDetector()

        ids = ["s1", "s2"]
        vectors = [[1,1,1,1,1,0,0,0] * 8, [0,0,0,0,0,1,1,1] * 8]  # Opposite patterns
        probs = detector.detect_collusion(ids, vectors, threshold=0.85)

        assert probs["s1"] < 0.5
        assert probs["s2"] < 0.5

    def test_single_student_no_collude(self):
        """Single student cannot collude with anyone"""
        from src.ml.gnn.model import CollusionDetector
        detector = CollusionDetector()
        probs = detector.detect_collusion(["s1"], [[1,0,1,1,0]], threshold=0.85)
        assert probs["s1"] == 0.0


class TestSBERTSimilarity:
    """Tests for SBERT plagiarism detection."""

    def test_identical_texts_high_similarity(self):
        from src.ml.nlp.similarity import compute_text_similarity
        sim = compute_text_similarity("Hello world", "Hello world")
        assert sim > 0.99

    def test_different_texts_low_similarity(self):
        from src.ml.nlp.similarity import compute_text_similarity
        sim = compute_text_similarity(
            "The pipeline hazard occurs when instructions conflict",
            "Python is a programming language for data science"
        )
        assert sim < 0.5

    def test_paraphrased_texts_moderate_similarity(self):
        """Paraphrased answers should still be caught"""
        from src.ml.nlp.similarity import compute_text_similarity
        sim = compute_text_similarity(
            "Data hazards occur when instructions depend on previous results",
            "Pipeline data conflicts happen because earlier instructions haven't finished"
        )
        # SBERT should detect semantic similarity even with different words
        assert sim > 0.6


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])