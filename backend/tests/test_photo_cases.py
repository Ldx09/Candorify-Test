"""The photo reader on real phone-read text from FAKE bills (data/photo_cases.json): each must give the right
charges, total, flags and payments. Run: pytest -q tests/test_photo_cases.py"""
import pytest

from scripts.evaluate_photos import CASES, check, json

CASE_LIST = json.loads(CASES.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASE_LIST, ids=[c["name"] for c in CASE_LIST])
def test_photo_case(case):
    assert check(case) == []