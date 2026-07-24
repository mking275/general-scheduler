"""Mountable router factories (D6).

``build_auth_router`` and ``build_admin_router`` return APIRouters bound to an
:class:`IdentityService`; products mount them under their own prefix with their
own hooks. Service errors are translated to HTTP status codes here — the service
itself stays transport-agnostic.
"""
from __future__ import annotations

from typing import Any, List, Optional

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Request
from pydantic import BaseModel

from ..errors import IdentityError
from ..models import SessionPair, Tenant
from .deps import get_current_user, require_cs_admin, require_role, require_superuser


async def _run(coro):
    """Await ``coro``, translating any :class:`IdentityError` to an HTTPException."""
    try:
        return await coro
    except IdentityError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


def _session_body(pair: SessionPair) -> dict:
    return {
        "access_token": pair.access_token,
        "refresh_token": pair.refresh_token,
        "cs_admin_scope": pair.cs_admin_scope,
        "user": pair.user.model_dump(mode="json"),
    }


class ExchangeRequest(BaseModel):
    external_token: str
    invitation_id: Optional[str] = None


class AcceptRequest(BaseModel):
    external_token: str
    invitation_id: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class SwitchTenantRequest(BaseModel):
    tenant_key: str


class EscapeHatchRequest(BaseModel):
    email: str
    password: str


class InviteRequest(BaseModel):
    email: str
    role: str
    tenant_key: str


class PatchUserRequest(BaseModel):
    role: Optional[str] = None
    customer_role: Optional[str] = None


def build_auth_router(service) -> APIRouter:
    """Auth surface: exchange, accept-invite, refresh, logout, switch-tenant, escape-hatch."""
    router = APIRouter(tags=["auth"])

    @router.post("/exchange")
    async def exchange(body: ExchangeRequest):
        pair = await _run(service.exchange_external_token(
            body.external_token, invitation_id=body.invitation_id,
        ))
        return _session_body(pair)

    @router.post("/accept-invitation")
    async def accept_invitation(body: AcceptRequest):
        pair = await _run(service.accept_invitation(body.external_token, body.invitation_id))
        return _session_body(pair)

    @router.post("/refresh")
    async def refresh(body: RefreshRequest):
        pair = await _run(service.refresh(body.refresh_token))
        return {"access_token": pair.access_token, "refresh_token": pair.refresh_token}

    @router.post("/logout")
    async def logout(body: LogoutRequest):
        await _run(service.logout(body.refresh_token))
        return {"detail": "logged out"}

    @router.post("/switch-tenant")
    async def switch_tenant(
        body: SwitchTenantRequest,
        current_user: dict = Depends(require_role("cs_admin")),
    ):
        access = await _run(service.switch_tenant(current_user, body.tenant_key))
        return {"access_token": access}

    @router.post("/escape-hatch")
    async def escape_hatch(
        request: Request,
        body: EscapeHatchRequest,
        x_escape_secret: str = Header(default=""),
    ):
        client_ip = request.client.host if request.client else "unknown"
        pair = await _run(service.escape_hatch_login(
            email=body.email, password=body.password, secret=x_escape_secret, client_ip=client_ip,
        ))
        return _session_body(pair)

    return router


def build_admin_router(service) -> APIRouter:
    """Admin surface (cs_admin+): users, invitations, tenants, audit."""
    router = APIRouter(tags=["admin"])

    @router.get("/users")
    async def list_users(
        tenant_key: Optional[str] = None,
        current_user: dict = Depends(require_cs_admin),
    ):
        users = await _run(service.list_users(current_user, tenant_key=tenant_key))
        return [u.model_dump(mode="json") for u in users]

    @router.patch("/users/{user_id}")
    async def patch_user(
        user_id: str, body: PatchUserRequest,
        current_user: dict = Depends(require_cs_admin),
    ):
        user = await _run(service.patch_user(
            current_user, user_id, role=body.role, customer_role=body.customer_role,
        ))
        return user.model_dump(mode="json")

    @router.post("/users/{user_id}/suspend")
    async def suspend(user_id: str, current_user: dict = Depends(require_cs_admin)):
        user = await _run(service.suspend(current_user, user_id))
        return user.model_dump(mode="json")

    @router.post("/users/{user_id}/reactivate")
    async def reactivate(user_id: str, current_user: dict = Depends(require_cs_admin)):
        user = await _run(service.reactivate(current_user, user_id))
        return user.model_dump(mode="json")

    @router.get("/users/{user_id}/audit-log")
    async def user_audit(user_id: str, current_user: dict = Depends(require_cs_admin)):
        recs = await _run(service.read_audit(current_user, target_user_id=user_id))
        return [r.model_dump(mode="json") for r in recs]

    @router.post("/invitations")
    async def create_invitation(
        body: InviteRequest, current_user: dict = Depends(require_cs_admin),
    ):
        inv = await _run(service.invite(
            current_user, email=body.email, role=body.role, tenant_key=body.tenant_key,
        ))
        return inv.model_dump(mode="json")

    @router.get("/invitations")
    async def list_invitations(
        tenant_key: Optional[str] = None, current_user: dict = Depends(require_cs_admin),
    ):
        invs = await _run(service.list_invitations(current_user, tenant_key=tenant_key))
        return [i.model_dump(mode="json") for i in invs]

    @router.post("/invitations/{invitation_id}/resend")
    async def resend_invitation(
        invitation_id: str, current_user: dict = Depends(require_cs_admin),
    ):
        inv = await _run(service.resend_invitation(current_user, invitation_id))
        return inv.model_dump(mode="json")

    @router.get("/tenants")
    async def list_tenants(current_user: dict = Depends(require_cs_admin)):
        tenants = await _run(service.list_tenants(current_user))
        return [t.model_dump(mode="json") for t in tenants]

    @router.post("/tenants")
    async def create_tenant(
        tenant: Tenant, current_user: dict = Depends(require_superuser),
    ):
        created = await _run(service.create_tenant(current_user, tenant))
        return created.model_dump(mode="json")

    return router
