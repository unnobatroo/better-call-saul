import time
from dataclasses import dataclass

from app.config import settings


@dataclass
class CircuitBreaker:
    """Fail fast against a broken provider, then probe periodically to recover."""

    failure_threshold: int = settings.circuit_failure_threshold
    recovery_seconds: float = settings.circuit_recovery_seconds

    _failures: int = 0
    _opened_at: float = 0.0

    def is_open(self) -> bool:
        if self._failures < self.failure_threshold:
            return False
        if time.monotonic() - self._opened_at >= self.recovery_seconds:
            self._failures = 0  # allow a probe through
            return False
        return True

    def record_success(self) -> None:
        self._failures = 0

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self.failure_threshold:
            self._opened_at = time.monotonic()
