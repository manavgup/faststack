"""Permission dependency factories for FastAPI routes.

These are v1 stubs that inspect ``request.state.user`` (populated by the
application's own auth middleware) and raise
:class:`~faststack_core.exceptions.domain.InsufficientPermissionsError`
when the required permission or role is missing.
"""

from collections.abc import Callable

from fastapi import Request

from faststack_core.exceptions.domain import InsufficientPermissionsError


def require_permission(permission: str) -> Callable:
    """Return a FastAPI dependency that checks *permission* on the current user.

    The dependency reads ``request.state.user`` and expects it to expose a
    ``permissions`` attribute (any iterable supporting ``in``).

    Usage::

        @router.get(
            "/admin",
            dependencies=[Depends(require_permission("admin:read"))],
        )
        async def admin_endpoint(): ...
    """

    async def dependency(request: Request) -> None:
        user = getattr(request.state, "user", None)
        if user is None:
            raise InsufficientPermissionsError("Authentication required")
        user_permissions = getattr(user, "permissions", [])
        if permission not in user_permissions:
            raise InsufficientPermissionsError(f"Missing permission: {permission}")

    return dependency


def require_role(role: str) -> Callable:
    """Return a FastAPI dependency that checks *role* on the current user.

    The dependency reads ``request.state.user`` and expects it to expose a
    ``roles`` attribute (any iterable supporting ``in``).

    Usage::

        @router.get(
            "/admin",
            dependencies=[Depends(require_role("admin"))],
        )
        async def admin_endpoint(): ...
    """

    async def dependency(request: Request) -> None:
        user = getattr(request.state, "user", None)
        if user is None:
            raise InsufficientPermissionsError("Authentication required")
        user_roles = getattr(user, "roles", [])
        if role not in user_roles:
            raise InsufficientPermissionsError(f"Missing role: {role}")

    return dependency
