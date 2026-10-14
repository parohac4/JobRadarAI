from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import get_settings


class CloudflareOnlyMiddleware(BaseHTTPMiddleware):
    """Volitelně odmítne přímý přístup na origin bez Cloudflare."""

    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        if settings.enforce_cloudflare and settings.is_production:
            if request.url.path.startswith("/api/"):
                if not request.headers.get("cf-connecting-ip"):
                    return JSONResponse(status_code=403, content={"detail": "Přístup jen přes Cloudflare"})
        return await call_next(request)
