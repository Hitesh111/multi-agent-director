import time
from unittest.mock import patch

import pytest

from llm.quota import QuotaTracker, get_quota_tracker
from llm.router import select_best_providers


class TestQuotaTracker:
    def test_tracks_rpm(self):
        t = QuotaTracker()
        t.record_request("grok")
        assert t.get_rpm("grok") == 1
        t.record_request("grok")
        assert t.get_rpm("grok") == 2

    def test_rpm_window_expires(self):
        t = QuotaTracker()
        t.record_request("grok")
        with patch("time.time", return_value=time.time() + 61):
            assert t.get_rpm("grok") == 0

    def test_daily_tracking(self):
        t = QuotaTracker()
        t.record_request("grok")
        assert t.get_daily_count("grok") == 1
        t.record_request("grok")
        assert t.get_daily_count("grok") == 2

    def test_daily_resets(self):
        t = QuotaTracker()
        t.record_request("grok")
        with patch("time.strftime", return_value="2099-01-01"):
            assert t.get_daily_count("grok") == 0

    def test_can_make_request_within_limits(self):
        t = QuotaTracker()
        assert t.can_make_request("grok", rpm_limit=30, daily_limit=7000) is True

    def test_cannot_exceed_rpm(self):
        t = QuotaTracker()
        for _ in range(30):
            t.record_request("grok")
        assert t.can_make_request("grok", rpm_limit=30, daily_limit=7000) is False

    def test_cannot_exceed_daily(self):
        t = QuotaTracker()
        for _ in range(1500):
            t.record_request("gemini")
        assert t.can_make_request("gemini", rpm_limit=60, daily_limit=1500) is False

    def test_usage_ratio(self):
        t = QuotaTracker()
        for _ in range(15):
            t.record_request("grok")
        ratio = t.get_usage_ratio("grok", rpm_limit=30, daily_limit=7000)
        assert 0.49 < ratio < 0.51  # 15/30 = 0.5


class TestQuotaRouter:
    def test_sorts_by_available_quota(self):
        t = QuotaTracker()
        for _ in range(20):
            t.record_request("gemini")
        for _ in range(2):
            t.record_request("grok")

        with patch("llm.router.get_quota_tracker", return_value=t):
            result = select_best_providers(["gemini", "grok", "deepseek"])

        assert result == ["deepseek", "grok"]  # gemini skipped (20/10 RPM exhausted)

    def test_skips_exhausted_providers(self):
        t = QuotaTracker()
        for _ in range(1500):
            t.record_request("gemini")

        with patch("llm.router.get_quota_tracker", return_value=t):
            result = select_best_providers(["gemini", "grok"])

        assert "gemini" not in result

    def test_fallback_to_all_if_all_exhausted(self):
        t = QuotaTracker()
        for _ in range(1500):
            t.record_request("gemini")
        for _ in range(31):
            t.record_request("grok")

        with patch("llm.router.get_quota_tracker", return_value=t):
            result = select_best_providers(["gemini", "grok"])

        assert result == ["gemini", "grok"]  # fallback to original order


@pytest.mark.django_db
class TestIntegration:
    def test_get_quota_tracker_singleton(self):
        a = get_quota_tracker()
        b = get_quota_tracker()
        assert a is b

    def test_record_and_check(self, settings):
        settings.PROVIDER_LIMITS = {"grok": {"rpm": 30, "daily": 7000}}
        tracker = get_quota_tracker()
        tracker.record_request("grok")
        assert tracker.can_make_request("grok", 30, 7000) is True
