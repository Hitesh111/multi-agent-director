import logging

from django.conf import settings

from .quota import get_quota_tracker

logger = logging.getLogger(__name__)

DEFAULT_LIMITS = {"rpm": 30, "daily": 5000}


def select_best_providers(providers: list[str]) -> list[str]:
    """Return providers sorted by most remaining quota, excluding exhausted ones.

    If all providers in the list are rate-limited, returns the original list
    as a fallback (so the caller can still attempt and get a proper error).
    """
    tracker = get_quota_tracker()
    provider_limits = getattr(settings, "PROVIDER_LIMITS", {})
    scored = []

    for p in providers:
        limits = provider_limits.get(p, DEFAULT_LIMITS)
        if tracker.can_make_request(p, limits["rpm"], limits["daily"]):
            ratio = tracker.get_usage_ratio(p, limits["rpm"], limits["daily"])
            scored.append((ratio, p))
        else:
            logger.info("Skipping %s — quota exhausted", p)

    if not scored:
        logger.warning("All providers rate-limited, falling back to original order")
        return providers

    scored.sort(key=lambda x: x[0])
    ordered = [p for _, p in scored]
    if ordered != providers:
        logger.info("Provider order (best first): %s", ordered)
    return ordered
