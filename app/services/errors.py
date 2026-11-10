"""Domain service errors → mapped to HTTP in routers."""

from __future__ import annotations


class ServiceError(Exception):
    def __init__(self, detail: str, *, status_code: int = 400) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


class NotFoundError(ServiceError):
    def __init__(self, detail: str = "Not found") -> None:
        super().__init__(detail, status_code=404)


class ForbiddenError(ServiceError):
    def __init__(self, detail: str = "Forbidden") -> None:
        super().__init__(detail, status_code=403)


class ConflictError(ServiceError):
    def __init__(self, detail: str = "Conflict") -> None:
        super().__init__(detail, status_code=409)
