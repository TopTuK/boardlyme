"""Google OAuth: authorization-code exchange and ID-token verification."""

import httpx
import jwt

from app.config import settings

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"

_jwks_client: jwt.PyJWKClient | None = None


def _jwks() -> jwt.PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = jwt.PyJWKClient(GOOGLE_JWKS_URL)
    return _jwks_client


async def exchange_code(code: str, redirect_uri: str) -> dict | None:
    """Trade an authorization code for Google tokens.

    Returns the decoded (unverified) `id_token` claims on success, None when
    Google rejects the exchange.
    """
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
    if resp.status_code != 200:
        return None
    id_token = resp.json().get("id_token")
    if not id_token:
        return None
    return verify_id_token(id_token)


def verify_id_token(id_token: str) -> dict | None:
    """Verify a Google ID token against Google's JWKS. Returns claims or None."""
    try:
        signing_key = _jwks().get_signing_key_from_jwt(id_token)
        claims = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.google_client_id,
            issuer=["https://accounts.google.com", "accounts.google.com"],
        )
    except jwt.PyJWTError:
        return None
    if not claims.get("sub"):
        return None
    return claims
