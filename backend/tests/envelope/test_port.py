"""Feature 009 — T007 PimsAdapterPort + registry acceptance.

- the port protocol imports and typechecks;
- an adapter registers and resolves through the registry;
- a static/import assertion confirms the core (state_machine.py) imports
  pims.port but NO concrete adapter module (no fork per PIMS).
"""
import ast
import os

from backend.envelope.pims import port
from backend.envelope.pims.port import (
    NormalizeResult, PimsAdapterPort, register_adapter, resolve_adapter,
)
from backend.models import FormatProfile


class _DummyAdapter:
    pims = "dummy"
    variant = "v1"

    def profile(self, raw_export):
        return FormatProfile(clinic_id="c", practice_id="p",
                             practice_database_id="x", export_variant="v1")

    def normalize(self, profile, raw_export):
        return NormalizeResult()


def test_port_protocol_typechecks():
    a = _DummyAdapter()
    assert isinstance(a, PimsAdapterPort)  # runtime_checkable Protocol


def test_register_and_resolve():
    register_adapter("dummy", "v1", lambda **kw: _DummyAdapter())
    resolved = resolve_adapter("dummy", "v1")
    assert isinstance(resolved, PimsAdapterPort)
    assert ("dummy", "v1") in port.registered_keys()


def test_wildcard_variant_fallback():
    register_adapter("dummy2", "*", lambda **kw: _DummyAdapter())
    # an unrecognized variant of a known PIMS resolves to the base adapter
    resolved = resolve_adapter("dummy2", "some_unknown_variant")
    assert isinstance(resolved, PimsAdapterPort)


def _imported_names(path: str) -> set[str]:
    """The dotted module names a file actually imports (AST — ignores docstring
    mentions)."""
    tree = ast.parse(open(path).read())
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
            names.update(f"{node.module}.{a.name}" for a in node.names)
    return names


def test_core_imports_port_not_concrete_adapter():
    """The orchestration core must import the port, never a concrete adapter."""
    root = os.path.dirname(os.path.dirname(port.__file__))  # backend/envelope
    core_modules = ["state_machine.py"]
    for mod in core_modules:
        imports = _imported_names(os.path.join(root, mod))
        assert not any("ezyvet_adapter" in i for i in imports), \
            f"{mod} must not import a concrete adapter"
    # the port module itself must not import a concrete adapter either
    assert not any("ezyvet_adapter" in i for i in _imported_names(port.__file__))
