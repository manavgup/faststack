"""Tests for the domain exception hierarchy and RFC 7807 handlers."""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from faststack_core.exceptions.domain import (
    EXCEPTION_STATUS_MAP,
    AlreadyExistsError,
    ConfigurationError,
    DomainError,
    ExternalServiceError,
    InsufficientPermissionsError,
    NotFoundError,
    OperationNotAllowedError,
    ResourceConflictError,
    ValidationError,
)
from faststack_core.exceptions.handlers import register_exception_handlers

# ---------------------------------------------------------------------------
# Test app fixture
# ---------------------------------------------------------------------------


def _build_app() -> FastAPI:
    """Return a minimal FastAPI app wired with domain exception handlers and
    test routes that raise each exception type."""
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/not-found")
    async def _not_found():
        raise NotFoundError("Thing not found")

    @app.get("/already-exists")
    async def _already_exists():
        raise AlreadyExistsError("Already exists")

    @app.get("/validation")
    async def _validation():
        raise ValidationError("Bad input", details={"field": "email", "reason": "invalid format"})

    @app.get("/operation-not-allowed")
    async def _operation_not_allowed():
        raise OperationNotAllowedError("Nope")

    @app.get("/resource-conflict")
    async def _resource_conflict():
        raise ResourceConflictError("Conflict detected")

    @app.get("/insufficient-permissions")
    async def _insufficient_permissions():
        raise InsufficientPermissionsError("Forbidden")

    @app.get("/external-service")
    async def _external_service():
        raise ExternalServiceError("Upstream broke")

    @app.get("/configuration")
    async def _configuration():
        raise ConfigurationError("Bad config")

    @app.get("/not-found-with-details")
    async def _not_found_with_details():
        raise NotFoundError("Missing", details={"id": "abc-123"})

    @app.get("/not-found-no-details")
    async def _not_found_no_details():
        raise NotFoundError("Missing")

    # An unmapped DomainError subclass -- should default to 500.
    class _UnknownDomainError(DomainError): ...

    @app.get("/unknown-domain-error")
    async def _unknown():
        raise _UnknownDomainError("Something unexpected")

    return app


@pytest.fixture
def app() -> FastAPI:
    return _build_app()


@pytest.fixture
async def client(app: FastAPI) -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# 1. Each exception class maps to the correct HTTP status code
# ---------------------------------------------------------------------------

_STATUS_CASES = [
    ("/not-found", 404, "NotFoundError"),
    ("/already-exists", 409, "AlreadyExistsError"),
    ("/validation", 422, "ValidationError"),
    ("/operation-not-allowed", 403, "OperationNotAllowedError"),
    ("/resource-conflict", 409, "ResourceConflictError"),
    ("/insufficient-permissions", 403, "InsufficientPermissionsError"),
    ("/external-service", 502, "ExternalServiceError"),
    ("/configuration", 500, "ConfigurationError"),
]


@pytest.mark.parametrize("path, expected_status, expected_title", _STATUS_CASES)
async def test_exception_status_codes(client, path, expected_status, expected_title):
    resp = await client.get(path)
    assert resp.status_code == expected_status
    body = resp.json()
    assert body["title"] == expected_title


# ---------------------------------------------------------------------------
# 2. RFC 7807 response has all required fields
# ---------------------------------------------------------------------------

_RFC7807_REQUIRED_FIELDS = {"type", "title", "status", "detail", "instance"}


@pytest.mark.parametrize("path, expected_status, _title", _STATUS_CASES)
async def test_rfc7807_required_fields(client, path, expected_status, _title):
    resp = await client.get(path)
    body = resp.json()
    assert _RFC7807_REQUIRED_FIELDS <= set(body.keys())
    assert body["status"] == expected_status
    assert body["instance"].startswith("http://test/")
    assert body["type"].startswith("/errors/")


# ---------------------------------------------------------------------------
# 3. details dict is included when provided, omitted when empty
# ---------------------------------------------------------------------------


async def test_details_included_when_provided(client):
    resp = await client.get("/not-found-with-details")
    body = resp.json()
    assert "details" in body
    assert body["details"] == {"id": "abc-123"}


async def test_details_omitted_when_empty(client):
    resp = await client.get("/not-found-no-details")
    body = resp.json()
    assert "details" not in body


async def test_validation_error_carries_details(client):
    resp = await client.get("/validation")
    body = resp.json()
    assert body["details"] == {"field": "email", "reason": "invalid format"}


# ---------------------------------------------------------------------------
# 4. Unknown DomainError subclass defaults to 500
# ---------------------------------------------------------------------------


async def test_unknown_domain_error_defaults_to_500(client):
    resp = await client.get("/unknown-domain-error")
    assert resp.status_code == 500
    body = resp.json()
    assert body["detail"] == "Something unexpected"
    assert body["status"] == 500


# ---------------------------------------------------------------------------
# 5. Explicit checks for NotFoundError (404), AlreadyExistsError (409),
#    and ValidationError (422)
# ---------------------------------------------------------------------------


async def test_not_found_error(client):
    resp = await client.get("/not-found")
    assert resp.status_code == 404
    body = resp.json()
    assert body["type"] == "/errors/NotFoundError"
    assert body["title"] == "NotFoundError"
    assert body["detail"] == "Thing not found"


async def test_already_exists_error(client):
    resp = await client.get("/already-exists")
    assert resp.status_code == 409
    body = resp.json()
    assert body["type"] == "/errors/AlreadyExistsError"
    assert body["title"] == "AlreadyExistsError"
    assert body["detail"] == "Already exists"


async def test_validation_error(client):
    resp = await client.get("/validation")
    assert resp.status_code == 422
    body = resp.json()
    assert body["type"] == "/errors/ValidationError"
    assert body["title"] == "ValidationError"
    assert body["detail"] == "Bad input"


# ---------------------------------------------------------------------------
# 6. EXCEPTION_STATUS_MAP completeness sanity check
# ---------------------------------------------------------------------------


def test_exception_status_map_covers_all_subclasses():
    expected = {
        NotFoundError,
        AlreadyExistsError,
        ValidationError,
        OperationNotAllowedError,
        ResourceConflictError,
        InsufficientPermissionsError,
        ExternalServiceError,
        ConfigurationError,
    }
    assert set(EXCEPTION_STATUS_MAP.keys()) == expected
