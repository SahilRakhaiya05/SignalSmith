from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.services.splunk_credentials import reset_splunk_auth, set_splunk_auth

logger = logging.getLogger("signalsmith.http")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
        auth_token = set_splunk_auth(
            request.headers.get("x-splunk-user"),
            request.headers.get("x-splunk-pass"),
        )
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("request_id=%s path=%s unhandled", request_id, request.url.path)
            raise
        finally:
            if auth_token is not None:
                reset_splunk_auth(auth_token)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = str(elapsed_ms)
        if not request.url.path.startswith("/assets"):
            logger.info(
                "request_id=%s method=%s path=%s status=%s ms=%s",
                request_id,
                request.method,
                request.url.path,
                response.status_code,
                elapsed_ms,
            )
        return response