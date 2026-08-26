from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class APIError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(APIError)
    async def handle_api_error(_: Request, exception: APIError) -> JSONResponse:
        return JSONResponse(
            status_code=exception.status_code,
            content={"error": {"code": exception.code, "message": exception.message}},
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exception: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "The request could not be validated.",
                    "details": exception.errors(),
                }
            },
        )