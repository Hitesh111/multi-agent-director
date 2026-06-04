import time
from collections import defaultdict, deque
from typing import Optional


PERMANENT_ERROR_CODES = {401, 402, 403}


class QuotaTracker:
    """Tracks per-provider request quotas using sliding-window RPM and daily counts.

    Also tracks permanently dead providers (402, auth errors) so they are
    skipped entirely instead of wasting time on repeated failed attempts.

    Thread-safe for async usage. Can be swapped for a Redis-backed version
    to share state across Celery workers.
    """

    def __init__(self):
        self._rpm: dict[str, deque] = defaultdict(deque)
        self._daily: dict[str, int] = defaultdict(int)
        self._daily_date: dict[str, str] = {}
        self.    _dead: set[str] = set()
    _cooldown: dict[str, float] = {}

    def record_request(self, provider: str) -> None:
        now = time.time()
        rpm_q = self._rpm[provider]
        rpm_q.append(now)
        while rpm_q and rpm_q[0] < now - 60:
            rpm_q.popleft()

        today = time.strftime("%Y-%m-%d")
        if self._daily_date.get(provider) != today:
            self._daily[provider] = 0
            self._daily_date[provider] = today
        self._daily[provider] += 1

    def mark_dead(self, provider: str) -> None:
        """Mark a provider as permanently dead (e.g., 402, auth error).
        Once dead, it will be skipped by select_best_providers."""
        self._dead.add(provider)

    def is_dead(self, provider: str) -> bool:
        return provider in self._dead

    def get_rpm(self, provider: str) -> int:
        now = time.time()
        rpm_q = self._rpm[provider]
        while rpm_q and rpm_q[0] < now - 60:
            rpm_q.popleft()
        return len(rpm_q)

    def get_daily_count(self, provider: str) -> int:
        today = time.strftime("%Y-%m-%d")
        if self._daily_date.get(provider) != today:
            return 0
        return self._daily[provider]

    def get_usage_ratio(self, provider: str, rpm_limit: int, daily_limit: int) -> float:
        """0.0–1.0 — higher means more quota consumed."""
        rpm_ratio = self.get_rpm(provider) / max(rpm_limit, 1)
        daily_ratio = self.get_daily_count(provider) / max(daily_limit, 1)
        return max(rpm_ratio, daily_ratio)

    def set_cooldown(self, provider: str, duration: float = 60.0) -> None:
        """Mark a provider as on cooldown (e.g., after a 429). It will be skipped
        for `duration` seconds. Useful for providers that rate-limit harder
        than our configured RPM limit suggests."""
        self._cooldown[provider] = time.time() + duration

    def _is_on_cooldown(self, provider: str) -> bool:
        deadline = self._cooldown.get(provider, 0.0)
        if deadline == 0.0:
            return False
        if time.time() < deadline:
            return True
        self._cooldown.pop(provider, None)
        return False

    def can_make_request(self, provider: str, rpm_limit: int, daily_limit: int) -> bool:
        if provider in self._dead:
            return False
        if self._is_on_cooldown(provider):
            return False
        if self.get_rpm(provider) >= rpm_limit:
            return False
        if self.get_daily_count(provider) >= daily_limit:
            return False
        return True


_tracker: Optional[QuotaTracker] = None


def get_quota_tracker() -> QuotaTracker:
    global _tracker
    if _tracker is None:
        _tracker = QuotaTracker()
    return _tracker
