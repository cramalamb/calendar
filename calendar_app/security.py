"""Security dependencies for the API."""

from __future__ import annotations

from fastapi import Header, HTTPException, status

from .config import require_api_key


async def verify_api_key(x_api_key: str = Header(..., convert_underscores=False)) -> None:
    """Ensure the provided API key header matches the configured key."""

    expected = require_api_key()
    if x_api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )
