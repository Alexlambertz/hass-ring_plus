class RingError(Exception):
    """Base error."""


class AuthError(RingError):
    """Invalid credentials or refresh token."""


class Requires2FA(AuthError):
    """Account needs a 2FA code; retry fetch_token with otp."""
