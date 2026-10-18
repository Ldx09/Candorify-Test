"""Every error the API returns has the same shape, so the frontend can always show `detail`:

    {"detail": "Human-readable message", "errors": [{"field": "...", "message": "..."}]}

`errors` is only present for form validation problems (HTTP 422).
"""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def _message(err: dict) -> str:
    """Turns a raw validation error into a sentence a user can read."""
    field = str(err["loc"][-1]) if err.get("loc") else "request"
    label = field.replace("_", " ").capitalize()
    kind = err.get("type", "")
    ctx = err.get("ctx") or {}
    if kind == "missing":
        return f"{label} is required"
    if field == "email":
        return "Please enter a valid email address"
    if kind == "string_too_short":
        return f"{label} must be at least {ctx.get('min_length')} characters"
    if kind == "string_too_long":
        return f"{label} must be at most {ctx.get('max_length')} characters"
    if kind == "json_invalid":
        return "Request body is not valid JSON"
    return err.get("msg", "Invalid value").removeprefix("Value error, ")


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        errors = [
            {"field": str(e["loc"][-1]) if e.get("loc") else "request", "message": _message(e)}
            for e in exc.errors()
        ]
        return JSONResponse(status_code=422, content={"detail": errors[0]["message"], "errors": errors})