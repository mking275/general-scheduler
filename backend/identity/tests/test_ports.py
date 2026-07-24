"""Ports & fake provider: protocol conformance and deterministic verification."""
import pytest

from cos_identity import (
    CollectingInviteDelivery,
    FakeIdentityProvider,
    IdentityProviderPort,
    InviteDeliveryPort,
    make_fake_token,
)
from cos_identity.models import Invitation


def test_fake_provider_satisfies_port():
    assert isinstance(FakeIdentityProvider(), IdentityProviderPort)
    assert isinstance(CollectingInviteDelivery(), InviteDeliveryPort)


async def test_fake_token_round_trip():
    p = FakeIdentityProvider()
    tok = make_fake_token("uid-1", "Person@Example.com", provider="microsoft", display_name="Person")
    ident = await p.verify_external_token(tok)
    assert ident.provider_uid == "uid-1"
    assert ident.email == "person@example.com"  # normalized
    assert ident.provider == "microsoft"
    assert ident.display_name == "Person"


async def test_fake_token_rejects_garbage():
    p = FakeIdentityProvider()
    with pytest.raises(ValueError):
        await p.verify_external_token("not-a-fake-token")


async def test_fake_provider_records_revocations():
    p = FakeIdentityProvider()
    await p.revoke_sessions("uid-1")
    assert p.revoked == ["uid-1"]


async def test_collecting_invite_delivery_collects():
    d = CollectingInviteDelivery()
    inv = Invitation(email="x@y.com", role="agent", tenant_key="t1")
    await d.send("x@y.com", "https://app/accept?invitation_id=1", inv)
    assert len(d.sent) == 1
    assert d.sent[0][0] == "x@y.com"
