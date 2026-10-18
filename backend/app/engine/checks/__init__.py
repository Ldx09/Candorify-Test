"""Deterministic check engine. Plain rules and arithmetic only: no AI in the error-finding step."""
from app.engine.checks.arithmetic import check_line_math, check_subtotal
from app.engine.checks.duplicates import check_duplicates
from app.engine.checks.engine import DETECTORS, run_checks

__all__ = ["run_checks", "DETECTORS", "check_duplicates", "check_line_math", "check_subtotal"]