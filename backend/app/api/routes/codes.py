"""Code -> plain English (NLM with offline fallback). Protected."""
from fastapi import APIRouter, Query

from app.translation.lookup import CodeInfo, System, lookup_code

router = APIRouter(prefix="/codes", tags=["codes"])


@router.get("/{code}", response_model=CodeInfo)
def get_code(code: str, system: System | None = Query(default=None, description="Optional: force the code system")):
    """Looks up a billing/diagnosis code. `source` says where the answer came from: nlm, fallback or not_found."""
    return lookup_code(code, system=system)