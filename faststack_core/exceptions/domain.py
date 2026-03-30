"""Domain exception hierarchy for FastStack.

All domain-level errors inherit from DomainError and carry a human-readable
message plus an optional details dict.  EXCEPTION_STATUS_MAP provides the
canonical mapping from exception type to HTTP status code.
"""


class DomainError(Exception):
    """Base class for all domain-level errors."""

    def __init__(self, message: str, details: dict | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class NotFoundError(DomainError): ...


class AlreadyExistsError(DomainError): ...


class ValidationError(DomainError): ...


class OperationNotAllowedError(DomainError): ...


class ResourceConflictError(DomainError): ...


class InsufficientPermissionsError(DomainError): ...


class ExternalServiceError(DomainError): ...


class ConfigurationError(DomainError): ...


EXCEPTION_STATUS_MAP: dict[type[DomainError], int] = {
    NotFoundError: 404,
    AlreadyExistsError: 409,
    ValidationError: 422,
    OperationNotAllowedError: 403,
    ResourceConflictError: 409,
    InsufficientPermissionsError: 403,
    ExternalServiceError: 502,
    ConfigurationError: 500,
}
