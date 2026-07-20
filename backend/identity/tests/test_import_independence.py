"""Core imports without FastAPI or firebase_admin on the path (T010/T022).

The Firebase adapter must import even when its SDK is absent (soft import); the
FastAPI extra must be the only place FastAPI is imported.
"""
import builtins
import importlib
import sys

CORE_MODULES = [
    "cos_identity.settings", "cos_identity.roles", "cos_identity.tokens",
    "cos_identity.passwords", "cos_identity.models", "cos_identity.ports",
    "cos_identity.service", "cos_identity.store", "cos_identity.tenancy",
    "cos_identity.audit", "cos_identity.errors",
]

_BLOCKED = ("fastapi", "firebase_admin")


def test_core_imports_with_fastapi_and_firebase_blocked(monkeypatch):
    real_import = builtins.__import__

    def guarded(name, *args, **kwargs):
        if name.split(".")[0] in _BLOCKED:
            raise ImportError(f"blocked: {name}")
        return real_import(name, *args, **kwargs)

    for mod in list(sys.modules):
        if mod.split(".")[0] in _BLOCKED:
            monkeypatch.delitem(sys.modules, mod, raising=False)
    for mod in [m for m in sys.modules if m.startswith("cos_identity")]:
        monkeypatch.delitem(sys.modules, mod, raising=False)

    monkeypatch.setattr(builtins, "__import__", guarded)
    for name in CORE_MODULES + ["cos_identity", "cos_identity.providers.firebase"]:
        importlib.import_module(name)

    assert "fastapi" not in sys.modules
    assert "firebase_admin" not in sys.modules
