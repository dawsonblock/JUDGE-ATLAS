"""Tests for the simple in-memory rate limiter."""

from app.core.rate_limit import SimpleRateLimiter, get_rate_limiter


class TestSimpleRateLimiter:
    """Test the SimpleRateLimiter class."""

    def test_check_allows_requests_under_limit(self):
        """Requests under the limit should be allowed."""
        limiter = SimpleRateLimiter()
        
        # Allow 3 requests
        for i in range(3):
            assert limiter.check("test_ip", limit=5) is True

    def test_check_blocks_requests_over_limit(self):
        """Requests over the limit should be blocked."""
        limiter = SimpleRateLimiter()
        
        # Allow 3 requests
        for i in range(3):
            assert limiter.check("test_ip", limit=3) is True
        
        # 4th request should be blocked
        assert limiter.check("test_ip", limit=3) is False

    def test_different_ips_have_separate_limits(self):
        """Different IP addresses should have separate rate limits."""
        limiter = SimpleRateLimiter()
        
        # IP1 makes 3 requests
        for i in range(3):
            assert limiter.check("192.168.1.1", limit=3) is True
        assert limiter.check("192.168.1.1", limit=3) is False
        
        # IP2 should still be allowed
        for i in range(3):
            assert limiter.check("192.168.1.2", limit=3) is True

    def test_old_requests_expire_after_window(self):
        """Old requests outside the time window should not count."""
        import time
        limiter = SimpleRateLimiter()
        
        # Make 3 requests
        for i in range(3):
            assert limiter.check("test_ip", limit=3) is True
        assert limiter.check("test_ip", limit=3) is False
        
        # Wait for window to expire (1 second window for testing)
        time.sleep(1.1)
        
        # New request should be allowed
        assert limiter.check("test_ip", limit=3, window=1) is True

    def test_reset_clears_specific_key(self):
        """Reset should clear requests for a specific key."""
        limiter = SimpleRateLimiter()
        
        # Make 3 requests
        for i in range(3):
            assert limiter.check("test_ip", limit=3) is True
        assert limiter.check("test_ip", limit=3) is False
        
        # Reset the key
        limiter.reset("test_ip")
        
        # Should be allowed again
        assert limiter.check("test_ip", limit=3) is True

    def test_reset_clears_all_keys(self):
        """Reset with None should clear all keys."""
        limiter = SimpleRateLimiter()
        
        # Make requests from multiple IPs
        for i in range(3):
            limiter.check("192.168.1.1", limit=3)
            limiter.check("192.168.1.2", limit=3)
        
        # Reset all
        limiter.reset()
        
        # Both IPs should be allowed again
        assert limiter.check("192.168.1.1", limit=3) is True
        assert limiter.check("192.168.1.2", limit=3) is True

    def test_get_rate_limiter_returns_singleton(self):
        """get_rate_limiter should return the same instance."""
        limiter1 = get_rate_limiter()
        limiter2 = get_rate_limiter()
        
        assert limiter1 is limiter2
