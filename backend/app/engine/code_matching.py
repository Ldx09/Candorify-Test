"""Matches a charge description from a real bill to a standard code, only when the match is clear.

Hospital summary bills list charges by department using the standard revenue-code category names
(e.g. "Emergency Room - General Classification" is revenue code 0450). Doctor statements often spell
out the visit type (e.g. "Office/Outpatient Established Mod Mdm" is CPT 99214).
Anything that isn't a clear match gets no code (""), and the description is kept as printed.
"""
import re

# (phrases that must ALL appear in the description, revenue code). More specific entries come first.
# Each phrase must start at a word boundary; a phrase ending in "\b" must also end at one
# (so "clinic\b" doesn't match "clinical").
REVENUE_CATEGORIES: list[tuple[tuple[str, ...], str]] = [
    (("pharmacy", "iv solution"), "0258"),
    (("pharmacy", "detailed coding"), "0636"),
    (("pharmacy", "self"), "0637"),
    (("pharmacy",), "0250"),
    (("iv therapy",), "0260"),
    (("supplies", "non-sterile"), "0271"),
    (("supplies", "sterile"), "0272"),
    (("supplies", "implant"), "0278"),
    (("medical/surgical supplies",), "0270"),
    (("laboratory pathology", "histology"), "0312"),
    (("laboratory pathology",), "0310"),
    (("laboratory", "chemistry"), "0301"),
    (("laboratory", "immunology"), "0302"),
    (("laboratory", "hematology"), "0305"),
    (("laboratory", "bacteriology"), "0306"),
    (("laboratory", "microbiology"), "0306"),
    (("laboratory", "urology"), "0307"),
    (("laboratory",), "0300"),
    (("radiology", "therapeutic"), "0330"),
    (("radiology",), "0320"),
    (("nuclear medicine",), "0340"),
    (("ct scan",), "0350"),
    (("computed tomography",), "0350"),
    (("operating room",), "0360"),
    (("anesthesia",), "0370"),
    (("blood", "storage"), "0390"),
    (("blood", "processing"), "0390"),
    (("mammography",), "0401"),
    (("ultrasound",), "0402"),
    (("respiratory",), "0410"),
    (("physical therap",), "0420"),
    (("occupational therap",), "0430"),
    (("speech", "therap"), "0440"),
    (("speech", "patholog"), "0440"),
    (("emergency room",), "0450"),
    (("cardiology",), "0480"),
    (("clinic\\b",), "0510"),
    (("ambulance",), "0540"),
    (("mri\\b",), "0610"),
    (("magnetic resonance",), "0610"),
    (("recovery room",), "0710"),
    (("ekg\\b",), "0730"),
    (("ecg\\b",), "0730"),
    (("treatment room",), "0761"),
    (("observation",), "0762"),
    (("intensive care",), "0200"),
    (("room", "board", "semi-private"), "0120"),
    (("room", "board", "private"), "0110"),
]

# Office visit level from the medical decision making (MDM) words printed on the statement.
_EM_LEVEL = [
    (re.compile(r"\b(straightforward|sf)\b"), 2),
    (re.compile(r"\b(low)\b"), 3),
    (re.compile(r"\b(mod|moderate)\b"), 4),
    (re.compile(r"\b(high)\b"), 5),
]


def match_code(description: str) -> str:
    """Returns the matching code, or "" when there is no clear match."""
    d = description.lower()
    if "office" in d and "outpatient" in d and ("mdm" in d or "decision" in d):
        visit = "9921" if "established" in d else "9920" if re.search(r"\bnew\b", d) else None
        if visit:
            for pattern, level in _EM_LEVEL:
                if pattern.search(d):
                    return f"{visit}{level}"
        return ""
    for phrases, code in REVENUE_CATEGORIES:
        if all(re.search(r"(?<![a-z])" + p, d) for p in phrases):
            return code
    return ""