"""FastAPI extra (D6). Import this package only when FastAPI is installed.

Kept isolated so the core imports cleanly without FastAPI on the path.
"""
from .deps import (
    build_current_user_dep,
    require_cs_admin,
    require_role,
    require_superuser,
)
from .routers import build_admin_router, build_auth_router

__all__ = [
    "build_current_user_dep",
    "require_role",
    "require_superuser",
    "require_cs_admin",
    "build_auth_router",
    "build_admin_router",
]
