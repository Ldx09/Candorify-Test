"""Shows the codes people looked up most that Candorify couldn't explain, so we know what to add next.

    python -m scripts.missing_codes_report          # top 50
    python -m scripts.missing_codes_report 200      # top 200

Add the ones that matter to data/cpt_codes.json (CPT) or data/medical_codes.json (everything else).
"""
import sys

from app.core.database import Base, SessionLocal, engine
from app.models import missing_code_record  # noqa: F401
from app.services.missing_codes import most_asked


def main() -> int:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    Base.metadata.create_all(bind=engine, tables=[missing_code_record.MissingCodeRecord.__table__])
    with SessionLocal() as db:
        rows = most_asked(db, limit)
    if not rows:
        print("No missing codes recorded yet.")
        return 0
    print(f"{'Code':10} {'Type':13} {'Asked':>5}  Last asked")
    for r in rows:
        print(f"{r.code:10} {r.system:13} {r.times_asked:>5}  {r.last_asked:%Y-%m-%d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())