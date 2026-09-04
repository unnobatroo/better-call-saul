from dataclasses import dataclass
from typing import TypedDict


class StatsSnapshot(TypedDict):
    successes: int
    failures: int
    success_rate: float | None
    avg_latency_ms: float | None
    total_cost: float


@dataclass
class ProviderStats:
    """Rolling metrics for one provider, fed by every request outcome."""

    successes: int = 0
    failures: int = 0
    total_latency_ms: float = 0.0
    total_cost: float = 0.0

    def record_success(self, latency_ms: float, cost: float) -> None:
        self.successes += 1
        self.total_latency_ms += latency_ms
        self.total_cost += cost

    def record_failure(self) -> None:
        self.failures += 1

    @property
    def success_rate(self) -> float | None:
        total = self.successes + self.failures
        return self.successes / total if total else None

    @property
    def avg_latency_ms(self) -> float | None:
        return self.total_latency_ms / self.successes if self.successes else None

    def as_dict(self) -> StatsSnapshot:
        return {
            "successes": self.successes,
            "failures": self.failures,
            "success_rate": self.success_rate,
            "avg_latency_ms": self.avg_latency_ms,
            "total_cost": round(self.total_cost, 4),
        }
