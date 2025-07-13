"""
Application-wide error handlers.
"""

import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.services.base import ServiceError

logger = logging.getLogger(__name__)


def setup_error_handlers(app: FastAPI) -> None:
    """Adds custom error handlers to the FastAPI app."""

    @app.exception_handler(ServiceError)
    async def handle_service_error(request: Request, exc: ServiceError) -> JSONResponse:
        """Handles controlled errors thrown from the service layer."""
        request_id = getattr(request.state, "request_id", "N/A")
        logger.warning(
            f"⚠️ ServiceError handled for request {request_id}: "
            f"Code='{exc.error_code}', Message='{exc.message}'"
        )
        return JSONResponse(
            status_code=400 if exc.error_code.startswith("VALIDATION") else 500,
            content={
                "error": {
                    "message": exc.message,
                    "type": exc.error_code,
                    "details": exc.details,
                }
            },
        )

    @app.exception_handler(Exception)
    async def handle_generic_exception(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handles any other unexpected exceptions."""
        request_id = getattr(request.state, "request_id", "N/A")
        logger.error(
            f"❌ Unhandled exception for request {request_id}: {exc}", exc_info=True
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "message": "An unexpected internal server error occurred.",
                    "type": "INTERNAL_SERVER_ERROR",
                    "request_id": request_id,
                }
            },
        )

    logger.info("✅ Custom error handlers have been set up.")
