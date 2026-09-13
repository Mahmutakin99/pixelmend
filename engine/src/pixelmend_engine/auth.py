"""Authenticate Electron main requests to a production sidecar."""

from secrets import compare_digest

from fastapi import Header, HTTPException, status

TOKEN_HEADER = "X-PixelMend-Token"
MINIMUM_TOKEN_CHARACTERS = 64


def require_session_token(expected_token: str):
    """Build a dependency that compares one production token in constant time."""
    if len(expected_token) < MINIMUM_TOKEN_CHARACTERS:
        raise ValueError("a production session token must contain at least 256 bits")

    def verify(token: str | None = Header(default=None, alias=TOKEN_HEADER)) -> None:
        """Reject a missing or mismatched sidecar request token."""
        if token is None or not compare_digest(token, expected_token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="valid session token required",
            )

    return verify
