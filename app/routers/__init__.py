# app/routers/__init__.py
"""
API Routers - Modular endpoint organization.

Note: File endpoints are defined in main.py to maintain proper path ordering.
"""
from .admin import router as admin_router
from .audit import router as audit_router
from .auth import router as auth_router
from .examples import router as examples_router
from .health import router as health_router
from .items import router as items_router
from .policy import router as policy_router
from .exceptions import router as exceptions_router
from .insights import insights_router
from .metrics import metrics_router
from .orchestrator import orchestrator_router
from .ai import router as ai_router

__all__ = [
    "health_router",
    "auth_router",
    "admin_router",
    "audit_router",
    "items_router",
    "examples_router",
    "policy_router",
    "exceptions_router",
    "insights_router",
    "orchestrator_router",
    "metrics_router",
    "ai_router",
]
