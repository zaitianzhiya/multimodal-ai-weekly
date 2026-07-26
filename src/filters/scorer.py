"""Scorer — compute confidence and quality scores for event records."""

from src.collectors.base import EventRecord


class Scorer:
    """Score events based on multi-source consensus and ecosystem independence.

    The scoring model:
      - confidence_score = weighted cross-ecosystem citation count (0-100)
      - confidence_grade = A/B/C/D based on thresholds
    """

    def __init__(self, config: dict):
        self.confidence = config.get("confidence", {})
        self.ecosystems = config.get("ecosystems", {})

    def score(self, records: list[EventRecord]) -> list[EventRecord]:
        for r in records:
            r.confidence_score = self._compute_confidence(r)
            r.confidence_grade = self._assign_grade(r.confidence_score)
        return records

    def _compute_confidence(self, record: EventRecord) -> float:
        """Cross-ecosystem independent citation score.

        Each unique ecosystem contributes weighted points:
        - Tier 1 source: 40 base points
        - Tier 2 source: 25 base points
        - Multiply by ecosystem independence_weight
        - Cap at 100
        """
        if not record.citations:
            return 0.0

        # Group by ecosystem, take best tier per ecosystem
        eco_best: dict[str, int] = {}
        for c in record.citations:
            tier_val = 2 if c.tier == 1 else 1
            eco_best[c.ecosystem] = max(eco_best.get(c.ecosystem, 0), tier_val)

        score = 0.0
        for eco, tier_val in eco_best.items():
            eco_weight = self.ecosystems.get(eco, {}).get("independence_weight", 1.0)
            base = 40 if tier_val == 2 else 25
            score += base * eco_weight

        return min(score, 100.0)

    def _assign_grade(self, score: float) -> str:
        for grade_key in ["grade_a", "grade_b", "grade_c", "grade_d"]:
            cfg = self.confidence.get(grade_key, {})
            if score >= cfg.get("threshold", 0):
                return cfg.get("label", grade_key[-1].upper())
        return "D"
