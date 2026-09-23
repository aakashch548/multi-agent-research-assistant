"""Application-wide exception hierarchy.

Every custom exception carries a machine-readable ``error_code``, a
human-readable ``message``, and a suggested HTTP status code so the
API layer can translate domain errors into proper responses without
leaking internal details.
"""

from __future__ import annotations

from http import HTTPStatus


class BaseAppException(Exception):
    """Root of the application exception hierarchy.

    All domain-specific exceptions derive from this class so they can
    be caught uniformly in middleware and error handlers.
    """

    error_code: str = "INTERNAL_ERROR"
    http_status: int = HTTPStatus.INTERNAL_SERVER_ERROR
    message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        error_code: str | None = None,
        http_status: int | None = None,
        details: dict | None = None,
    ) -> None:
        self.message = message or self.__class__.message
        if error_code is not None:
            self.error_code = error_code
        if http_status is not None:
            self.http_status = http_status
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """Serialise the exception for JSON responses."""
        payload: dict = {
            "error_code": self.error_code,
            "message": self.message,
        }
        if self.details:
            payload["details"] = self.details
        return payload


class AgentExecutionError(BaseAppException):
    """Raised when an individual agent fails during execution."""

    error_code = "AGENT_EXECUTION_ERROR"
    http_status = HTTPStatus.INTERNAL_SERVER_ERROR
    message = "An agent failed during execution."

    def __init__(
        self,
        message: str | None = None,
        *,
        agent_name: str | None = None,
        error_code: str | None = None,
        http_status: int | None = None,
        details: dict | None = None,
    ) -> None:
        details = details or {}
        if agent_name:
            details["agent_name"] = agent_name
        super().__init__(
            message,
            error_code=error_code,
            http_status=http_status,
            details=details,
        )


class WorkflowError(BaseAppException):
    """Raised when the orchestration workflow encounters an error."""

    error_code = "WORKFLOW_ERROR"
    http_status = HTTPStatus.INTERNAL_SERVER_ERROR
    message = "A workflow error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        workflow_name: str | None = None,
        step: str | None = None,
        error_code: str | None = None,
        http_status: int | None = None,
        details: dict | None = None,
    ) -> None:
        details = details or {}
        if workflow_name:
            details["workflow_name"] = workflow_name
        if step:
            details["step"] = step
        super().__init__(
            message,
            error_code=error_code,
            http_status=http_status,
            details=details,
        )


class RAGError(BaseAppException):
    """Raised for retrieval-augmented generation pipeline failures."""

    error_code = "RAG_ERROR"
    http_status = HTTPStatus.INTERNAL_SERVER_ERROR
    message = "A RAG pipeline error occurred."


class DatabaseError(BaseAppException):
    """Raised when a database operation fails."""

    error_code = "DATABASE_ERROR"
    http_status = HTTPStatus.SERVICE_UNAVAILABLE
    message = "A database error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        operation: str | None = None,
        error_code: str | None = None,
        http_status: int | None = None,
        details: dict | None = None,
    ) -> None:
        details = details or {}
        if operation:
            details["operation"] = operation
        super().__init__(
            message,
            error_code=error_code,
            http_status=http_status,
            details=details,
        )


class ExternalServiceError(BaseAppException):
    """Raised when a call to an external service fails."""

    error_code = "EXTERNAL_SERVICE_ERROR"
    http_status = HTTPStatus.BAD_GATEWAY
    message = "An external service request failed."

    def __init__(
        self,
        message: str | None = None,
        *,
        service_name: str | None = None,
        status_code: int | None = None,
        error_code: str | None = None,
        http_status: int | None = None,
        details: dict | None = None,
    ) -> None:
        details = details or {}
        if service_name:
            details["service_name"] = service_name
        if status_code is not None:
            details["upstream_status_code"] = status_code
        super().__init__(
            message,
            error_code=error_code,
            http_status=http_status,
            details=details,
        )


class AppValidationError(BaseAppException):
    """Raised for domain-level validation failures.

    Named ``AppValidationError`` to avoid shadowing Pydantic's
    ``ValidationError``.
    """

    error_code = "VALIDATION_ERROR"
    http_status = HTTPStatus.UNPROCESSABLE_ENTITY
    message = "Validation failed."

    def __init__(
        self,
        message: str | None = None,
        *,
        field: str | None = None,
        error_code: str | None = None,
        http_status: int | None = None,
        details: dict | None = None,
    ) -> None:
        details = details or {}
        if field:
            details["field"] = field
        super().__init__(
            message,
            error_code=error_code,
            http_status=http_status,
            details=details,
        )


# Mapping kept at module level so middleware can do a single isinstance
# check against BaseAppException and call to_dict() without needing to
# know the concrete subclass.
HTTP_STATUS_MAP: dict[type[BaseAppException], int] = {
    AgentExecutionError: HTTPStatus.INTERNAL_SERVER_ERROR,
    WorkflowError: HTTPStatus.INTERNAL_SERVER_ERROR,
    RAGError: HTTPStatus.INTERNAL_SERVER_ERROR,
    DatabaseError: HTTPStatus.SERVICE_UNAVAILABLE,
    ExternalServiceError: HTTPStatus.BAD_GATEWAY,
    AppValidationError: HTTPStatus.UNPROCESSABLE_ENTITY,
}
