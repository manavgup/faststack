# ADR-004: RFC 7807 Error Responses with Domain Exception Hierarchy

- *Status:* Accepted
- *Date:* 2026-03-30
- *Deciders:* Manav
- *Related:* [ADR-005](005-crud-service-lifecycle-hooks.md)

## Context

FastAPI's default error handling uses `HTTPException`, which couples business logic to HTTP status codes. This means service-layer code like `raise HTTPException(status_code=404)` knows about HTTP — a layer violation.

We need error handling that:
1. Keeps business logic HTTP-free (services raise domain errors, not HTTP errors)
2. Returns structured, machine-readable error responses
3. Maps domain errors to HTTP status codes at the boundary (exception handlers)

RFC 7807 ("Problem Details for HTTP APIs") is an IETF standard for structured error responses. It defines fields: `type`, `title`, `status`, `detail`, `instance`.

## Decision

**Domain exception hierarchy + RFC 7807 global exception handlers.**

Domain exceptions in `faststack_core`:
- `DomainError` (base) — message + optional details dict
- `NotFoundError` → 404
- `AlreadyExistsError` → 409
- `ValidationError` → 422
- `OperationNotAllowedError` → 403
- `ResourceConflictError` → 409
- `InsufficientPermissionsError` → 403
- `ExternalServiceError` → 502
- `ConfigurationError` → 500

Global exception handler registered by `setup_app()`:
```json
{
  "type": "/errors/NotFoundError",
  "title": "NotFoundError",
  "status": 404,
  "detail": "User 123 not found",
  "instance": "/users/123"
}
```

Services raise `NotFoundError("User not found")`, never `HTTPException(status_code=404)`.

## Consequences

### Positive
- Business logic is HTTP-free — services are testable without HTTP context
- Consistent error format across all endpoints — clients parse one schema
- RFC 7807 is an industry standard — interoperable with API clients that support it
- Exception hierarchy is extensible — users add entity-specific exceptions

### Negative
- Developers accustomed to `HTTPException` need to learn the domain exception pattern
- The exception-to-status mapping (`EXCEPTION_MAP`) must be maintained as new exceptions are added
- RFC 7807 adds a `type` URI field that needs to resolve to documentation (or be opaque)

### Neutral
- Pydantic `ValidationError` from request parsing still returns FastAPI's default 422 — only domain `ValidationError` goes through our handler

## Alternatives Considered

| Option | Why Not |
|--------|---------|
| FastAPI's built-in `HTTPException` everywhere | Couples business logic to HTTP. Services can't be tested without HTTP context. Layer violation. |
| Custom JSON error format (non-standard) | Reinventing what RFC 7807 already standardizes. Clients would need custom parsing. |
| Error codes (integer-based) | Less descriptive than exception classes. Harder to maintain. The exception hierarchy IS the error code system. |

## Configuration

Exception handlers can be disabled via `FastStackConfig(exception_handlers=False)` for users who want to register their own handlers.

## References

- [RFC 7807 — Problem Details for HTTP APIs](https://www.rfc-editor.org/rfc/rfc7807)
- [FastAPI exception handling docs](https://fastapi.tiangolo.com/tutorial/handling-errors/)
