"""Every error the API returns has the same shape, so the frontend can always show `detail`:

    {"detail": "Human-readable message", "errors": [{"field": "...", "message": "..."}]}

`errors` is only present for form validation problems (HTTP 422).
For errors inside a bill line, `field` looks like "lines.2.unit_price" and the message starts with "Line 3:".
"""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def _field_path(loc: tuple) -> str:
    parts = [str(p) for p in loc if p not in ("body", "query", "path")]
    return ".".join(parts) or "request"


def _message(err: dict) -> str:
    """Turns a raw validation error into a sentence a user can read."""
    loc = [p for p in err.get("loc", ()) if p not in ("body", "query", "path")]
    field = str(loc[-1]) if loc else "request"
    label = field.replace("_", " ").capitalize()
    # Errors inside a list of lines, e.g. ("lines", 2, "unit_price") -> "Line 3: Unit price ..."
    prefix = ""
    if len(loc) >= 3 and loc[0] == "lines" and isinstance(loc[1], int):
        prefix = f"Line {loc[1] + 1}: "
    kind = err.get("type", "")
    ctx = err.get("ctx") or {}

    if kind == "missing":
        msg = f"{label} is required"
    elif field == "email":
        msg = "Please enter a valid email address"
    elif kind == "string_too_short":
        msg = f"{label} must be at least {ctx.get('min_length')} characters"
    elif kind == "string_too_long":
        msg = f"{label} must be at most {ctx.get('max_length')} characters"
    elif kind == "too_short":
        msg = f"{label} must have at least {ctx.get('min_length')} item(s)"
    elif kind == "too_long":
        msg = f"{label} can have at most {ctx.get('max_length')} items"
    elif kind == "greater_than":
        msg = f"{label} must be more than {ctx.get('gt')}"
    elif kind == "greater_than_equal":
        msg = f"{label} cannot be negative" if str(ctx.get("ge")) == "0" else f"{label} must be at least {ctx.get('ge')}"
    elif kind == "decimal_max_places":
        msg = f"{label} can have at most {ctx.get('decimal_places')} decimal places"
    elif kind == "decimal_max_digits":
        msg = f"{label} is too large"
    elif kind in ("decimal_parsing", "decimal_type", "int_parsing", "float_parsing"):
        msg = f"{label} must be a number"
    elif kind == "json_invalid":
        msg = "Request body is not valid JSON"
    else:
        msg = err.get("msg", "Invalid value").removeprefix("Value error, ")
    return prefix + msg


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        errors = [{"field": _field_path(e.get("loc", ())), "message": _message(e)} for e in exc.errors()]
        return JSONResponse(status_code=422, content={"detail": errors[0]["message"], "errors": errors})