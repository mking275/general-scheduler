"""D1/R1 — the broker posture is entered by exactly three service methods.

``app.identity_broker='on'`` is the only path to cross-tenant visibility for the
non-scoped lookups login requires. This test proves, by static analysis, that no
code outside exchange_external_token / accept_invitation / refresh enters it.
"""
import ast
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "cos_identity"
ALLOWED = {"exchange_external_token", "accept_invitation", "refresh"}
BROKER_CALLS = {"_broker_ctx", "_broker_context"}


def _enclosing_functions_calling(tree, names):
    """Map each function whose body contains a call to one of ``names``."""
    hits = set()

    class Visitor(ast.NodeVisitor):
        def __init__(self):
            self.stack = []

        def _visit_func(self, node):
            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

        visit_FunctionDef = _visit_func
        visit_AsyncFunctionDef = _visit_func

        def visit_Call(self, node):
            func = node.func
            attr = getattr(func, "attr", None)
            ident = getattr(func, "id", None)
            if attr in names or ident in names:
                # attribute to the nearest enclosing named function
                if self.stack:
                    hits.add(self.stack[-1])
            self.generic_visit(node)

    Visitor().visit(tree)
    return hits


def test_broker_context_only_in_three_service_methods():
    tree = ast.parse((SRC / "service.py").read_text(encoding="utf-8"))
    callers = _enclosing_functions_calling(tree, BROKER_CALLS)
    # The _broker_ctx helper method itself constructs the context manager; exclude it.
    callers.discard("_broker_ctx")
    assert callers <= ALLOWED, f"broker entered from unexpected methods: {callers - ALLOWED}"
    assert callers == ALLOWED, f"a broker method stopped using the broker context: {ALLOWED - callers}"


def test_broker_context_not_imported_outside_service_and_tenancy():
    offenders = []
    for path in SRC.rglob("*.py"):
        if path.name in ("service.py", "tenancy.py"):
            continue
        if "_broker_context" in path.read_text(encoding="utf-8"):
            offenders.append(str(path))
    assert not offenders, f"_broker_context referenced outside service/tenancy: {offenders}"
