"""State hospital financial assistance rules, on top of the federal rules for nonprofit hospitals.

Only what each state's law guarantees is listed; every hospital can be more generous, and the patient's own
hospital decides. Checked November 2026 against state agency pages, statutes and the Commonwealth Fund /
Triage Cancer state surveys. Review every year (laws change; Maine's new rule started July 1, 2026).

levels: [(income up to % of the poverty guideline, % taken off the patient's bill or None = discount set by
the hospital/state formula)], lowest income first.
who:   "all" (insured or not), "uninsured", or "uninsured_or_underinsured".
"""

STATE_PROGRAMS = {
    "CA": dict(name="California Hospital Fair Pricing Act", who="uninsured_or_underinsured",
               levels=[(400, None)],
               summary="Every hospital (including for-profit) must offer free or discounted care up to 400% of the "
                       "guideline to uninsured patients and to insured patients with high medical costs. Discounted "
                       "bills are capped near what Medicare would pay.",
               source=None),
    "CO": dict(name="Colorado Hospital Discounted Care", who="uninsured", levels=[(250, None)], monthly_cap_pct=4,
               summary="Uninsured patients up to 250% of the guideline get discounted hospital rates. Monthly "
                       "payments can't be more than 4% of your monthly household income, and after 36 monthly "
                       "payments the rest of the bill is forgiven.",
               source="https://hcpf.colorado.gov/colorado-hospital-discounted-care"),
    "CT": dict(name="Connecticut uninsured patient protections", who="uninsured", levels=[(250, None)],
               summary="Uninsured patients up to 250% of the guideline can't be charged more than the hospital's "
                       "cost of care.",
               source=None),
    "DE": dict(name="Delaware medical debt protections", who="uninsured_or_underinsured", levels=[(350, None)],
               summary="Hospitals must offer financial assistance to uninsured and underinsured patients up to 350% "
                       "of the guideline (underinsured: out-of-pocket costs of at least 5% of income).",
               source=None),
    "GA": dict(name="Georgia Indigent Care Trust Fund", who="all", levels=[(125, 100), (200, None)],
               summary="At hospitals in the Indigent Care Trust Fund, Georgia residents below 125% of the guideline "
                       "can have the bill forgiven, with a sliding scale up to 200%.",
               source=None),
    "IL": dict(name="Illinois Hospital Uninsured Patient Discount Act", who="uninsured",
               levels=[(200, 100), (600, None)],
               alt=("At rural and critical access hospitals", [(125, 100), (300, None)]),
               summary="Uninsured Illinois residents get free care up to 200% of the guideline (for charges over "
                       "$150) and a discount up to 600%: the bill can't be more than the hospital's cost plus 35%. "
                       "There's also a yearly cap on what can be collected, tied to your income.",
               source="https://ilga.gov/legislation/ilcs/documents/021000890K10.htm"),
    "MA": dict(name="Massachusetts Health Safety Net", who="uninsured_or_underinsured",
               levels=[(150, 100), (300, None)],
               summary="Massachusetts residents up to 150% of the guideline get hospital bills fully covered; from "
                       "150% to 300% they're covered after a yearly deductible.",
               source=None),
    "MD": dict(name="Maryland hospital financial assistance", who="all", levels=[(200, 100), (300, None)],
               summary="Every Maryland hospital must give free care up to 200% of the guideline and reduced-cost care "
                       "from 200% to 300% (up to 500% with a financial hardship). People on SNAP or LIHEAP, or with "
                       "kids getting free school lunch, qualify for free care automatically.",
               source="https://mhaonline.org/wp-content/uploads/2024/05/Overview-of-Programs.pdf"),
    "ME": dict(name="Maine hospital free care", who="all", levels=[(200, 100)],
               summary="Since July 1, 2026, Maine hospitals must give free care to patients up to 200% of the "
                       "guideline.",
               source=None),
    "MI": dict(name="Michigan uninsured pricing limit", who="uninsured", levels=[(250, None)],
               summary="At hospitals in Medicaid, uninsured patients up to 250% of the guideline can't be charged "
                       "more than 115% of what Medicare pays.",
               source=None),
    "MN": dict(name="Minnesota uninsured pricing limit", who="uninsured", levels=[],
               summary="Hospitals can't charge uninsured patients with household income under $125,000 more than "
                       "they charge their most-favored insurance company.",
               source=None),
    "NJ": dict(name="New Jersey Charity Care", who="all",
               levels=[(200, 100), (225, 80), (250, 60), (275, 40), (300, 20)],
               summary="Every acute care hospital in New Jersey must give free care up to 200% of the guideline and a "
                       "sliding discount up to 300%. Assets limit: $7,500 for one person, $15,000 for a family. You "
                       "can apply up to 1 year after the service.",
               deadline="You can apply up to 1 year after the date of service.",
               source="https://www.nj.gov/health/charitycare/"),
    "NM": dict(name="New Mexico Patients' Debt Collection Protection Act", who="all", levels=[(200, 100)],
               summary="Hospitals can't try to collect a bill from patients up to 200% of the guideline.",
               source=None),
    "NV": dict(name="Nevada uninsured discount", who="uninsured", levels=[],
               summary="Larger hospitals must take at least 30% off inpatient bills for uninsured patients.",
               source=None),
    "NY": dict(name="New York Hospital Financial Assistance Law", who="uninsured_or_underinsured",
               levels=[(200, 100), (300, 90), (400, 80)], monthly_cap_pct=5,
               summary="Uninsured and underinsured patients (medical bills over 10% of income) up to 400% of the "
                       "guideline qualify. Under 200%: nothing to pay. 200% to 300%: at most 10% (of the Medicaid "
                       "rate if uninsured, or of your insurance cost-sharing). 300% to 400%: at most 20%. Payment "
                       "plans can't be more than 5% of monthly income, and hospitals can't sue patients under 400%.",
               source="https://ag.ny.gov/resources/individuals/health-care-insurance/hospital-financial-assistance"),
    "OH": dict(name="Ohio Hospital Care Assurance Program", who="all", levels=[(100, 100)],
               summary="Ohio residents at or below 100% of the guideline get basic hospital care free.",
               source=None),
    "OR": dict(name="Oregon hospital financial assistance (nonprofit hospitals)", who="all",
               levels=[(200, 100), (300, 75), (350, 50), (400, 25)],
               summary="Nonprofit hospitals must take 100% off up to 200% of the guideline, 75% off up to 300%, 50% "
                       "off up to 350% and 25% off up to 400%, whether or not you have insurance.",
               source="https://www.oregonlaws.org/ors/442.614"),
    "RI": dict(name="Rhode Island hospital uncompensated care rules", who="all", levels=[(200, 100), (300, None)],
               summary="Hospitals must give free care up to 200% of the guideline and a discount from 200% to 300%.",
               source=None),
    "SC": dict(name="South Carolina Medically Indigent Assistance Program", who="all", levels=[],
               summary="The state Medically Indigent Assistance Program may pay hospital bills for residents with low "
                       "income (up to about 200% of the guideline). Apply within a year of discharge.",
               source=None),
    "TN": dict(name="Tennessee uninsured pricing limit", who="uninsured", levels=[],
               summary="Hospitals can't charge uninsured patients more than 175% of the hospital's cost of care.",
               source=None),
    "VA": dict(name="Virginia charity care conditions", who="all", levels=[],
               summary="Many Virginia hospitals must give free care up to 200% of the guideline as a condition of "
                       "their state approval (Certificate of Public Need). Ask if yours does.",
               source=None),
    "VT": dict(name="Vermont hospital financial assistance", who="all", levels=[(250, 100), (400, None)],
               summary="Larger Vermont hospitals must give free care up to 250% of the guideline and discounts up to "
                       "400%; bills are capped at 20% of household income up to 600%.",
               source=None),
    "WA": dict(name="Washington Charity Care Act", who="all", levels=[(200, 100), (250, 75), (300, 50)],
               alt=("At large hospital systems", [(300, 100), (350, 75), (400, 50)]),
               summary="Every Washington hospital must give charity care, insured or not. Smaller hospitals: free up "
                       "to 200% of the guideline, 75% off up to 250%, 50% off up to 300%. Large hospital systems: "
                       "free up to 300%, 75% off up to 350%, 50% off up to 400%.",
               source="https://doh.wa.gov/data-and-statistical-reports/healthcare-washington/hospital-and-patient-data/hospital-patient-information-and-charity-care"),
}

# Used when a state has no source link of its own: a state-by-state table of charity care laws.
STATE_TABLE_SOURCE = "https://triagecancer.org/state-laws/charity-care"

# States that have NOT adopted the ACA Medicaid expansion (KFF, 2026). Everywhere else, adults up to about
# 138% of the guideline can get Medicaid.
MEDICAID_NOT_EXPANDED = {"AL", "FL", "GA", "KS", "MS", "SC", "TN", "TX", "WI", "WY"}
MEDICAID_ADULT_LIMIT = 138