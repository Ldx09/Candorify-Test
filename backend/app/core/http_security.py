"""HTTP hardening: HTTPS redirect (production only) and security headers on every response."""
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse

from app.core.config import settings

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",         # browsers must not guess content types
    "X-Frame-Options": "DENY",                   # the API can't be embedded in someone else's page
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",                 # bills and tokens are never cached by browsers/proxies
}
HSTS = "max-age=31536000; includeSubDomains"     # browsers only use HTTPS for this host for a year


def add_http_security(app: FastAPI) -> None:
    @app.middleware("http")
    async def _security(request: Request, call_next):
        if settings.ENV == "production":
            # The host (e.g. Render) ends TLS and tells us the original scheme in X-Forwarded-Proto.
            proto = request.headers.get("x-forwarded-proto", request.url.scheme)
            if proto == "http" and request.url.path != "/health":
                return RedirectResponse(str(request.url.replace(scheme="https")), status_code=308)
        response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        if settings.ENV == "production":
            response.headers["Strict-Transport-Security"] = HSTS
        return response