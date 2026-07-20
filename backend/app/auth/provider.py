from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends

from app.auth.errors import InvalidJwt
from app.auth.jwt import DevJwtVerifier, GoogleJwtVerifier, JwtClaims, JwtVerifier
from app.config import Settings, get_settings


@dataclass(frozen=True, slots=True)
class UnsupportedJwtVerifier:
    """Fail-closed verifier used until a real OIDC/JWKS provider is configured."""

    provider: str

    async def verify(self, token: str) -> JwtClaims:
        raise InvalidJwt()


def build_jwt_verifier(settings: Settings) -> JwtVerifier:
    if settings.auth_oidc_provider == "dev":
        return DevJwtVerifier(
            provider=settings.auth_oidc_provider,
            issuer=settings.auth_oidc_issuer,
            audience=settings.auth_oidc_audience,
        )
    if settings.auth_oidc_provider == "google" and settings.auth_oidc_audience:
        return GoogleJwtVerifier(audience=settings.auth_oidc_audience)
    return UnsupportedJwtVerifier(provider=settings.auth_oidc_provider)


def get_jwt_verifier(settings: Settings = Depends(get_settings)) -> JwtVerifier:
    return build_jwt_verifier(settings)
