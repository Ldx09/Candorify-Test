"""GET /api/translate?code=  -- the one endpoint the frontend calls for code -> plain English. Protected."""
from fastapi import APIRouter, Query

from app.translation.service import CodeInfo, System, lookup_code

router = APIRouter(tags=["translate"])


@router.get("/translate", response_model=CodeInfo)
def translate(
    code: str = Query(min_length=1, max_length=20, description="Billing or diagnosis code, e.g. J2405, 99284, R10.9"),
    system: System | None = Query(default=None, description="Optional: force the code system"),
):
    """Looks up the code: cache -> NLM -> offline dictionary.
    `source` says where the answer came from (nlm / fallback / not_found); `cached` is true for cache hits."""
    return lookup_code(code, system=system)