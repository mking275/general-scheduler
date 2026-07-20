"""Firebase identity + invite-delivery adapter (D5).

``firebase_admin`` and ``httpx`` are soft-imported inside the methods so this
module always imports even when the SDK is absent (the dev/sim environment). The
live paths raise a clear error until a Firebase project is provisioned; the
Secret-Manager location for the web API key is configured, never hardcoded.
"""
from __future__ import annotations

from typing import Optional

from ..models import Invitation, VerifiedIdentity
from ..settings import IdentitySettings

_PROVIDER_MAP = {"google.com": "google", "microsoft.com": "microsoft"}


def _map_provider(sign_in_provider: str) -> str:
    """Map a Firebase ``sign_in_provider`` string to the component's enum."""
    for needle, value in _PROVIDER_MAP.items():
        if needle.split(".")[0] in sign_in_provider:
            return value
    return "password"


class FirebaseIdentityProvider:
    """Adapter over Firebase Auth. Verification only; revocation at the DB layer.

    Mirrors the FA2 finding: ``check_revoked=False`` — the internal refresh store
    is the revocation source of truth, not Firebase token state.
    """

    def __init__(self, settings: IdentitySettings) -> None:
        self._settings = settings
        self._app = None

    def _ensure_app(self):
        """Lazily initialize the Firebase app; raises if the SDK is unavailable."""
        if self._app is not None:
            return self._app
        try:
            import firebase_admin  # noqa: PLC0415 — soft import; absent in sim env
        except ImportError as exc:  # pragma: no cover - depends on optional dep
            raise RuntimeError(
                "firebase_admin is not installed; use the fake provider or install the extra"
            ) from exc
        if not firebase_admin._apps:  # type: ignore[attr-defined]
            firebase_admin.initialize_app()
        self._app = firebase_admin.get_app()
        return self._app

    async def verify_external_token(self, external_token: str) -> VerifiedIdentity:
        """Verify a Firebase ID token and map it to a :class:`VerifiedIdentity`."""
        self._ensure_app()
        from firebase_admin import auth as fb_auth  # noqa: PLC0415

        claims = fb_auth.verify_id_token(external_token, check_revoked=False)
        email = (claims.get("email") or "").lower()
        if not email:
            raise ValueError("Firebase token missing email claim")
        sign_in_provider = claims.get("firebase", {}).get("sign_in_provider", "")
        return VerifiedIdentity(
            provider_uid=claims["uid"],
            email=email,
            provider=_map_provider(sign_in_provider),
            display_name=claims.get("name") or claims.get("display_name"),
        )

    async def revoke_sessions(self, provider_uid: str) -> None:
        """Revoke the subject's Firebase refresh tokens (called on suspend)."""
        self._ensure_app()
        from firebase_admin import auth as fb_auth  # noqa: PLC0415

        fb_auth.revoke_refresh_tokens(provider_uid)


class FirebaseInviteDelivery:
    """Invite delivery via Identity-Toolkit ``sendOobCode`` (EMAIL_SIGNIN).

    The web API key is read from the configured Secret-Manager location
    (``firebase_web_api_key_secret``); nothing is hardcoded.
    """

    def __init__(self, settings: IdentitySettings) -> None:
        self._settings = settings

    def _web_api_key(self) -> str:
        """Fetch the Firebase web API key from its configured secret location."""
        secret_name = self._settings.firebase_web_api_key_secret
        if not secret_name:
            raise RuntimeError("firebase_web_api_key_secret is not configured")
        try:
            from google.cloud import secretmanager  # noqa: PLC0415
        except ImportError as exc:  # pragma: no cover - optional dep
            raise RuntimeError("google-cloud-secret-manager not installed") from exc
        client = secretmanager.SecretManagerServiceClient()
        resp = client.access_secret_version(name=secret_name)
        return resp.payload.data.decode()

    async def send(self, email: str, accept_url: str, invitation: Invitation) -> None:
        """Send an email sign-in link with ``accept_url`` as the continue URL."""
        import httpx  # noqa: PLC0415

        api_key = self._web_api_key()
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={api_key}",
                json={
                    "requestType": "EMAIL_SIGNIN",
                    "email": email,
                    "continueUrl": accept_url,
                    "canHandleCodeInApp": True,
                },
            )
            resp.raise_for_status()


def build_firebase_provider(settings: IdentitySettings) -> FirebaseIdentityProvider:
    """Factory for the Firebase provider (kept out of module import time)."""
    return FirebaseIdentityProvider(settings)
