"""
AI Usage & LLM Token Tracker Unit Tests.
"""

from app.core.ai_tracker import record_ai_usage, get_ai_usage_summary


def test_ai_tracker_records_tokens():
    """Verifies token recording increments totals and daily values."""
    before = get_ai_usage_summary()
    initial_requests = before["total_requests"]
    initial_tokens = before["total_tokens"]

    # Record 400 tokens (300 prompt + 100 completion)
    record_ai_usage(prompt_tokens=300, completion_tokens=100, total_tokens=400)

    after = get_ai_usage_summary()
    assert after["total_requests"] == initial_requests + 1
    assert after["total_tokens"] == initial_tokens + 400
    assert after["today_requests"] >= 1
    assert after["today_tokens"] >= 400
    assert "percent_used" in after
    assert after["status"] in ["normal", "warning"]


def test_ai_tracker_summary_structure():
    """Verifies get_ai_usage_summary contains all required fields for Admin UI."""
    summary = get_ai_usage_summary()
    required_keys = [
        "model_name", "total_requests", "total_tokens",
        "today_requests", "today_tokens", "daily_limit",
        "percent_used", "status", "last_used_at"
    ]
    for key in required_keys:
        assert key in summary
