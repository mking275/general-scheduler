"""Role hierarchy: ranking, rank ceiling, invitable-role derivation."""
from cos_identity import roles


def test_rank_order():
    assert roles.rank("viewer") < roles.rank("agent") < roles.rank("cs_admin") < roles.rank("superuser")
    assert roles.rank("nonsense") == -1


def test_has_rank():
    assert roles.has_rank("superuser", "cs_admin")
    assert roles.has_rank("cs_admin", "cs_admin")
    assert not roles.has_rank("agent", "cs_admin")
    assert not roles.has_rank("", "viewer")


def test_invitable_roles_ceiling():
    # cs_admin may invite strictly below its rank; never a peer or superior.
    assert set(roles.invitable_roles("cs_admin")) == {"agent", "viewer"}
    assert set(roles.invitable_roles("superuser")) == {"cs_admin", "agent", "viewer"}
    assert roles.invitable_roles("agent") == ["viewer"]
    assert roles.invitable_roles("viewer") == []


def test_can_grant_role():
    assert roles.can_grant_role("superuser", "cs_admin")
    assert roles.can_grant_role("cs_admin", "agent")
    assert not roles.can_grant_role("cs_admin", "cs_admin")
    assert not roles.can_grant_role("cs_admin", "superuser")
    assert not roles.can_grant_role("agent", "cs_admin")
