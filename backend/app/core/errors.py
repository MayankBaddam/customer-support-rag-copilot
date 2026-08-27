from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException


class APIError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code


HTTP_ERROR_DEFAULTS = {
    400: ("BAD_REQUEST", "The request could not be completed."),
    401: ("AUTHENTICATION_REQUIRED", "Authentication is required."),
    403: ("ACCESS_FORBIDDEN", "You do not have permission to perform this action."),
    404: ("NOT_FOUND", "The requested resource was not found."),
    422: ("VALIDATION_ERROR", "The request could not be validated."),
    429: ("RATE_LIMITED", "Too many requests. Please try again later."),
    500: ("INTERNAL_SERVER_ERROR", "The server could not complete the request."),
}


def _request_id(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    if request_id is None:
        request_id = str(uuid4())
        request.state.request_id = request_id
    return str(request_id)


def _error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        headers=headers,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": _request_id(request),
            }
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(APIError)
    async def handle_api_error(request: Request, exception: APIError) -> JSONResponse:
        return _error_response(
            request,
            status_code=exception.status_code,
            code=exception.code,
            message=exception.message,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, _: RequestValidationError) -> JSONResponse:
        return _error_response(
            request,
            status_code=422,
            code="VALIDATION_ERROR",
            message="The request could not be validated.",
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exception: StarletteHTTPException) -> JSONResponse:
        code, message = HTTP_ERROR_DEFAULTS.get(
            exception.status_code,
            ("REQUEST_FAILED", "The request could not be completed."),
        )
        return _error_response(
            request,
            status_code=exception.status_code,
            code=code,
            message=message,
            headers=exception.headers,
        )

    @app.exception_handler(SQLAlchemyError)
    async def handle_database_error(request: Request, _: SQLAlchemyError) -> JSONResponse:
        return _error_response(
            request,
            status_code=500,
            code="DATABASE_ERROR",
            message="The database operation could not be completed.",
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, _: Exception) -> JSONResponse:
        return _error_response(
            request,
            status_code=500,
            code="INTERNAL_SERVER_ERROR",
            message="The server could not complete the request.",
        )
