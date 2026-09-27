import logging
from collections.abc import Mapping
from http import HTTPStatus

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from kalibra_engine.shared.infrastructure.external_provider_error import ExternalProviderError

logger = logging.getLogger(__name__)

_PROBLEM_JSON = "application/problem+json"
_PROVIDER_FAILURE_DETAIL = "Un proveedor externo de IA no respondió correctamente."
_BAD_GATEWAY = HTTPStatus.BAD_GATEWAY.value


class EngineExceptionHandler:
    """Translate engine exceptions into RFC 9457 ``application/problem+json`` responses.

    FastAPI keeps resolving its own errors (``HTTPException``, request validation);
    this handler only covers the exceptions it is given plus external provider failures.

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
        status = self._status_for(exc)
        if status == _BAD_GATEWAY:
            logger.warning("External provider failure on %s: %r", request.url.path, exc)
            detail = _PROVIDER_FAILURE_DETAIL
        else:
            detail = str(exc)
        return JSONResponse(
            status_code=status,
            media_type=_PROBLEM_JSON,
            content={
                "type": "about:blank",
                "title": HTTPStatus(status).phrase,
                "status": status,
                "detail": detail,
                "instance": request.url.path,
            },
        )

    def _status_for(self, exc: Exception) -> int:
        for exception_type in type(exc).__mro__:
            if exception_type in self._status_by_exception:
                return self._status_by_exception[exception_type]
        return HTTPStatus.INTERNAL_SERVER_ERROR.value
