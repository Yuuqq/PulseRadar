# coding=utf-8

from __future__ import annotations

from unittest.mock import patch


# ---------------------------------------------------------------------------
# Rate Limiter tests
# ---------------------------------------------------------------------------

def test_rate_limiter_first_request_no_wait():
    """First request for a key should not sleep."""
    from trendradar.crawler.middleware.rate_limiter import RateLimiter

    limiter = RateLimiter(default_rps=2.0)

    with patch("trendradar.crawler.middleware.rate_limiter.time") as mock_time:
        # Simulate: first call at t=100, no prior request
        mock_time.monotonic.return_value = 100.0
        limiter.wait("key_a")
        mock_time.sleep.assert_not_called()


def test_rate_limiter_enforces_interval():
    """Second request within the interval should trigger a sleep."""
    from trendradar.crawler.middleware.rate_limiter import RateLimiter

    limiter = RateLimiter(default_rps=2.0)  # min_interval = 0.5s

    with patch("trendradar.crawler.middleware.rate_limiter.time") as mock_time:
        call_count = [0]

        def advancing_monotonic():
            call_count[0] += 1
            if call_count[0] <= 2:
                return 100.0  # First wait(): check + record
            return 100.1  # Second wait(): only 0.1s elapsed (< 0.5s)

        mock_time.monotonic.side_effect = advancing_monotonic

        limiter.wait("key_a")
        # Reset side_effect for second call
        call_count[0] = 0

        def second_call_monotonic():
            call_count[0] += 1
            if call_count[0] == 1:
                return 100.1  # 0.1s since last (recorded at 100.0)
            return 100.6  # After sleep, record new time

        mock_time.monotonic.side_effect = second_call_monotonic
        limiter.wait("key_a")
        mock_time.sleep.assert_called_once()
        sleep_duration = mock_time.sleep.call_args[0][0]
        assert 0.3 < sleep_duration < 0.5  # Should sleep ~0.4s (0.5 - 0.1)


def test_rate_limiter_per_key_isolation():
    """Different keys should have independent rate limits."""
    from trendradar.crawler.middleware.rate_limiter import RateLimiter

    limiter = RateLimiter(default_rps=1.0)  # min_interval = 1.0s

    with patch("trendradar.crawler.middleware.rate_limiter.time") as mock_time:
        t = [100.0]

        def monotonic_advancing():
            val = t[0]
            t[0] += 0.01
            return val

        mock_time.monotonic.side_effect = monotonic_advancing

        limiter.wait("key_a")
        limiter.wait("key_b")  # Different key, should not sleep

        # sleep should not be called: key_a has no prior, key_b has no prior
        mock_time.sleep.assert_not_called()


def test_rate_limiter_custom_rps():
    """Custom rps should override the default."""
    from trendradar.crawler.middleware.rate_limiter import RateLimiter

    limiter = RateLimiter(default_rps=1.0)

    with patch("trendradar.crawler.middleware.rate_limiter.time") as mock_time:
        call_count = [0]

        def monotonic_first():
            call_count[0] += 1
            if call_count[0] <= 2:
                return 100.0
            return 100.0

        mock_time.monotonic.side_effect = monotonic_first
        limiter.wait("fast", rps=10.0)  # min_interval = 0.1s
        mock_time.sleep.assert_not_called()


# ---------------------------------------------------------------------------
# Circuit Breaker tests
# ---------------------------------------------------------------------------

def test_circuit_breaker_initial_state_is_closed():
    from trendradar.crawler.middleware.circuit_breaker import CircuitBreaker

    cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=60.0)
    assert cb.allow_request("svc_a") is True


def test_circuit_breaker_closed_to_open_after_threshold():
    from trendradar.crawler.middleware.circuit_breaker import CircuitBreaker

    cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=60.0)

    # 3 consecutive failures should trip the breaker
    cb.record_failure("svc_a")
    assert cb.allow_request("svc_a") is True  # count=1, still closed
    cb.record_failure("svc_a")
    assert cb.allow_request("svc_a") is True  # count=2, still closed
    cb.record_failure("svc_a")
    # count=3 -> OPEN
    assert cb.allow_request("svc_a") is False


def test_circuit_breaker_open_to_half_open_after_cooldown():
    from trendradar.crawler.middleware.circuit_breaker import CircuitBreaker

    cb = CircuitBreaker(failure_threshold=2, cooldown_seconds=10.0)

    with patch("trendradar.crawler.middleware.circuit_breaker.time") as mock_time:
        mock_time.monotonic.return_value = 100.0
        cb.record_failure("svc")
        cb.record_failure("svc")
        # Now OPEN at t=100

        # Still within cooldown
        mock_time.monotonic.return_value = 105.0
        assert cb.allow_request("svc") is False

        # After cooldown (10s from last failure at 100)
        mock_time.monotonic.return_value = 111.0
        assert cb.allow_request("svc") is True
        # State should now be HALF_OPEN
        assert cb._states["svc"] == CircuitBreaker.HALF_OPEN


def test_circuit_breaker_half_open_to_closed_on_success():
    from trendradar.crawler.middleware.circuit_breaker import CircuitBreaker

    cb = CircuitBreaker(failure_threshold=2, cooldown_seconds=5.0)

    with patch("trendradar.crawler.middleware.circuit_breaker.time") as mock_time:
        mock_time.monotonic.return_value = 100.0
        cb.record_failure("svc")
        cb.record_failure("svc")
        # OPEN

        mock_time.monotonic.return_value = 106.0
        assert cb.allow_request("svc") is True  # -> HALF_OPEN

        cb.record_success("svc")
        assert cb._states["svc"] == CircuitBreaker.CLOSED
        assert cb._failure_counts["svc"] == 0


def test_circuit_breaker_half_open_to_open_on_failure():
    from trendradar.crawler.middleware.circuit_breaker import CircuitBreaker

    cb = CircuitBreaker(failure_threshold=2, cooldown_seconds=5.0)

    with patch("trendradar.crawler.middleware.circuit_breaker.time") as mock_time:
        mock_time.monotonic.return_value = 100.0
        cb.record_failure("svc")
        cb.record_failure("svc")
        # OPEN

        mock_time.monotonic.return_value = 106.0
        cb.allow_request("svc")  # -> HALF_OPEN

        # Another failure in HALF_OPEN => back to OPEN
        mock_time.monotonic.return_value = 107.0
        cb.record_failure("svc")
        # failure_count is now 3, which >= threshold=2, so OPEN again
        assert cb._states["svc"] == CircuitBreaker.OPEN


def test_circuit_breaker_keys_are_independent():
    from trendradar.crawler.middleware.circuit_breaker import CircuitBreaker

    cb = CircuitBreaker(failure_threshold=2, cooldown_seconds=60.0)
    cb.record_failure("svc_a")
    cb.record_failure("svc_a")  # svc_a -> OPEN

    assert cb.allow_request("svc_a") is False
    assert cb.allow_request("svc_b") is True  # svc_b is independent
