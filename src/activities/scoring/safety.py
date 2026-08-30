"""Generic Safety Gate primitives shared by coastal activities."""
from __future__ import annotations

from dataclasses import dataclass, field


def _score(value: float) -> float:
    number = float(value)
    if not 0 <= number <= 100:
        raise ValueError("score/cap values must be between 0 and 100")
    return number


@dataclass
class SafetyDecision:
    """Accumulate explicit penalties, caps and hard stops with fixed precedence."""

    penalties: list[tuple[float, str]] = field(default_factory=list)
    caps: list[tuple[float, str]] = field(default_factory=list)
    hard_stops: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    def _reason(self, reason: str) -> str:
        value = str(reason).strip()
        if not value:
            raise ValueError("reason is required")
        return value

    def add_penalty(self, points: float, reason: str) -> None:
        value = float(points)
        if not 0 < value <= 100:
            raise ValueError("penalty must be greater than 0 and at most 100")
        reason = self._reason(reason)
        self.penalties.append((value, reason))
        self.reasons.append(reason)

    def add_cap(self, cap: float, reason: str) -> None:
        value = _score(cap)
        reason = self._reason(reason)
        self.caps.append((value, reason))
        self.reasons.append(reason)

    def add_hard_stop(self, reason: str) -> None:
        reason = self._reason(reason)
        self.hard_stops.append(reason)
        self.reasons.append(reason)

    def apply(self, quality_score: float) -> dict:
        quality = _score(quality_score)
        penalty = round(sum(points for points, _ in self.penalties), 1)
        cap = round(min((value for value, _ in self.caps), default=100.0), 1)

        if self.hard_stops:
            return {
                "raw_quality_score": quality,
                "penalty": penalty,
                "cap": cap,
                "hard_stop": True,
                "status": "NOT RECOMMENDED",
                "final_score": None,
                "reasons": list(self.reasons),
            }

        after_penalty = max(0.0, quality - penalty)
        final = round(min(after_penalty, cap), 1)
        return {
            "raw_quality_score": quality,
            "penalty": penalty,
            "cap": cap,
            "hard_stop": False,
            "status": "normal",
            "final_score": final,
            "reasons": list(self.reasons),
        }
