import logging
from collections.abc import Mapping
from http import HTTPStatus
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from kalibra_engine.shared.infrastructure.external_provider_error import ExternalProviderError

logger = logging.getLogger(__name__)

PROBLEM_JSON = "application/problem+json"
_PROVIDER_FAILURE_DETAIL = "Un proveedor externo de IA no respondió correctamente."
_INTERNAL_FAILURE_DETAIL = "Error interno del engine."
_BAD_GATEWAY = HTTPStatus.BAD_GATEWAY.value
_INTERNAL_SERVER_ERROR = HTTPStatus.INTERNAL_SERVER_ERROR.value


def problem_details(status: int, detail: str, instance: str) -> dict[str, Any]:
    """Build an RFC 9457 problem-details body.

    Args:
        status: HTTP status code.
        detail: Human-readable explanation.
        instance: Where the problem happened (request path or task reference).

    Returns:
        The problem-details object.
    """
    return {
        "type": "about:blank",
        "title": HTTPStatus(status).phrase,
        "status": status,
        "detail": detail,
        "instance": instance,
    }


class EngineExceptionHandler:
    """Translate engine exceptions into RFC 9457 ``application/problem+json`` bodies.

    FastAPI keeps resolving its own errors (``HTTPException``, request validation);
    this handler covers the exceptions it is given plus external provider failures, for
    both REST responses and task results.

    Args:
        status_by_exception: HTTP status for each business exception type, supplied by
            the composition root so that ``shared`` never imports a bounded context.
    """

    def __init__(self, status_by_exception: Mapping[type[Exception], int]) -> None:
        self._status_by_exception: dict[type[Exception], int] = {
            ExternalProviderError: _BAD_GATEWAY,
            httpx.HTTPError: _BAD_GATEWAY,
            **status_by_exception,
        }

    def register(self, app: FastAPI) -> None:
        """Register one handler per mapped exception type on the application.

        Args:
            app: The FastAPI application.
        """
        for exception_type in self._status_by_exception:
            app.add_exception_handler(exception_type, self.handle)

    async def handle(self, request: Request, exc: Exception) -> JSONResponse:
        """Build the problem-details response for ``exc``.

        Args:
            request: The request that failed.
            exc: The raised exception.

        Returns:
            A ``JSONResponse`` with the mapped status and problem-details body.
        """
        problem = self.problem_for(exc, request.url.path)
        return JSONResponse(status_code=problem["status"], media_type=PROBLEM_JSON, content=problem)

    def problem_for(self, exc: Exception, instance: str) -> dict[str, Any]:
        """Map an exception to its problem-details body without leaking internals.

        Business exceptions keep their message; provider failures and unmapped errors get
        a generic detail and are logged instead.

        Args:
            exc: The raised exception.
            instance: Where the problem happened.

        Returns:
            The problem-details object.
        """
        status = self._status_for(exc)
        if status == _BAD_GATEWAY:
            logger.warning("External provider failure on %s: %r", instance, exc)
            detail = _PROVIDER_FAILURE_DETAIL
        elif status == _INTERNAL_SERVER_ERROR:
            logger.error("Unexpected failure on %s", instance, exc_info=exc)
            detail = _INTERNAL_FAILURE_DETAIL
        else:
            detail = str(exc)
        return problem_details(status, detail, instance)

    def _status_for(self, exc: Exception) -> int:
        for exception_type in type(exc).__mro__:
            if exception_type in self._status_by_exception:
                return self._status_by_exception[exception_type]
        return _INTERNAL_SERVER_ERROR
