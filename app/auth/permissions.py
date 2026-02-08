"""Role-based permission guards for metrics endpoints (P5.M3.T6).

Roles are extracted from the ``X-User-Role`` request header.  When the
environment variable ``TASCADE_AUTH_DISABLED`` is set to a truthy value
(e.g. ``"1"``), permission checks are bypassed entirely so that the
existing test suite is unaffected.
"""

from __future__ import annotations

import os
from typing import Callable

from fastapi import Depends, HTTPException, Request

# ---------------------------------------------------------------------------
# Role constants
# ---------------------------------------------------------------------------

PLANNER: str = "planner"
REVIEWER: str = "reviewer"
OPERATOR: str = "operator"

# ---------------------------------------------------------------------------
# Permission matrix: role -> set of allowed endpoint keys
# ---------------------------------------------------------------------------

PERMISSION_MATRIX: dict[str, set[str]] = {
    PLANNER: {
        "summary",
        "trends",
        "breakdown",
        "drilldown",
        "health",
        "alerts",
        "alerts:acknowledge",
        "actions",
    },
    REVIEWER: {
        "summary",
        "trends",
        "breakdown",
        "drilldown",
        "health",
        "alerts",
    },
    OPERATOR: {
        "summary",
        "trends",
        "breakdown",
    },
}


# ---------------------------------------------------------------------------
# Role extraction
# ---------------------------------------------------------------------------


def get_user_role(request: Request) -> str:
    """Extract the user role from the ``X-User-Role`` header.

    Returns the lowercased value.  If the header is absent, defaults to
    ``"planner"``.
    """
    raw = request.headers.get("x-user-role", PLANNER)
    return raw.lower()


# ---------------------------------------------------------------------------
# Permission guard factory
# ---------------------------------------------------------------------------


def _is_auth_disabled() -> bool:
    """Return ``True`` when permission checks should be skipped."""
    return bool(os.environ.get("TASCADE_AUTH_DISABLED"))


def require_permission(endpoint_key: str) -> Callable[..., None]:
    """FastAPI ``Depends()`` factory that checks role-based access.

    Usage::

        @app.get("/v1/metrics/summary")
        def get_metrics_summary(
            _perm: None = Depends(require_permission("summary")),
            ...
        ):
            ...

    When ``TASCADE_AUTH_DISABLED`` is set, the guard is a no-op.
    Otherwise it resolves the user role from the request and verifies the
    role has the *endpoint_key* in its permission set.  Returns 403 if
    access is denied.
    """

    def _guard(request: Request) -> None:
        if _is_auth_disabled():
            return

        role = get_user_role(request)
        allowed = PERMISSION_MATRIX.get(role)

        if allowed is None or endpoint_key not in allowed:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": {
                        "code": "PERMISSION_DENIED",
                        "message": f"Role '{role}' does not have access to '{endpoint_key}'",
                        "retryable": False,
                    }
                },
            )

    return _guard
