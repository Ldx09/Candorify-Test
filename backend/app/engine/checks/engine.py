"""Check-engine runner: runs every detector on a bill and returns one structured flag report.
Deterministic: plain rules and arithmetic only, no AI. Same bill in -> same flags out."""
from app.engine.checks.arithmetic import check_line_math, check_subtotal
from app.engine.checks.duplicates import check_duplicates
from app.engine.models import FlagReport
from app.models.bill import Bill

# Every detector takes a Bill and returns a list of Flags. Add new detectors here.
DETECTORS = [check_duplicates, check_line_math, check_subtotal]


def run_checks(bill: Bill) -> FlagReport:
    """Runs all detectors and returns the flags sorted by line (bill-level flags last)."""
    flags = [flag for detector in DETECTORS for flag in detector(bill)]
    flags.sort(key=lambda f: (f.line_no is None, f.line_no or 0, f.rule))
    return FlagReport(bill_id=bill.bill_id, flag_count=len(flags), flags=flags)