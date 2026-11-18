"""Financial assistance checker: compares household income with the federal poverty guidelines (the measure
hospital assistance policies use), adds the patient's state rules (app/engine/state_assistance.py) and
Medicaid, and turns that into a dollar estimate, next steps and a ready letter.

Says only "you may qualify": the hospital decides. Nothing here is stored. Not legal or financial advice.
Update POVERTY_GUIDELINES every January from https://aspe.hhs.gov/poverty-guidelines
"""
import math
from decimal import ROUND_HALF_UP, Decimal

from app.engine.state_assistance import (MEDICAID_ADULT_LIMIT, MEDICAID_NOT_EXPANDED, STATE_PROGRAMS,
                                         STATE_TABLE_SOURCE)

GUIDELINE_YEAR = 2026
# (first person, each additional person), HHS 2026 poverty guidelines
POVERTY_GUIDELINES = {
    "default": (15960, 5680),   # 48 contiguous states and DC
    "AK": (19950, 7100),
    "HI": (18360, 6530),
}
US_STATES = set("AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM "
                "NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY".split())
STATE_NAMES = dict(AL="Alabama", AK="Alaska", AZ="Arizona", AR="Arkansas", CA="California", CO="Colorado",
                   CT="Connecticut", DE="Delaware", DC="the District of Columbia", FL="Florida", GA="Georgia",
                   HI="Hawaii", ID="Idaho", IL="Illinois", IN="Indiana", IA="Iowa", KS="Kansas", KY="Kentucky",
                   LA="Louisiana", ME="Maine", MD="Maryland", MA="Massachusetts", MI="Michigan", MN="Minnesota",
                   MS="Mississippi", MO="Missouri", MT="Montana", NE="Nebraska", NV="Nevada", NH="New Hampshire",
                   NJ="New Jersey", NM="New Mexico", NY="New York", NC="North Carolina", ND="North Dakota",
                   OH="Ohio", OK="Oklahoma", OR="Oregon", PA="Pennsylvania", RI="Rhode Island", SC="South Carolina",
                   SD="South Dakota", TN="Tennessee", TX="Texas", UT="Utah", VT="Vermont", VA="Virginia",
                   WA="Washington", WV="West Virginia", WI="Wisconsin", WY="Wyoming")
SUGGESTED_PLAN_PCT = 5       # a payment plan of about 5% of monthly income (New York's legal cap) is a fair ask
FEDERAL_DEADLINE = ("Apply within 240 days of the first bill you got after the visit. Nonprofit hospitals must "
                    "accept applications for at least that long.")


def _money(x) -> str:
    return f"${Decimal(x):,.2f}"


def poverty_line(household: int, state: str | None) -> int:
    first, extra = POVERTY_GUIDELINES.get((state or "").upper(), POVERTY_GUIDELINES["default"])
    return first + extra * (household - 1)


def _level(levels, percent):
    """(% taken off, income limit) of the first level the income fits in, or None above every level."""
    for upto, off in levels:
        if percent <= upto:
            return off, upto
    return None


def _state_result(state: str | None, percent: int, insured: bool | None) -> dict | None:
    prog = STATE_PROGRAMS.get(state or "")
    if not prog:
        return None
    applies, note = True, None
    if prog["who"] == "uninsured" and insured:
        applies, note = False, "This state rule is for patients without insurance, so it may not apply to you."
    elif prog["who"] == "uninsured" and insured is None:
        note = "This state rule is for patients without insurance."
    elif prog["who"] == "uninsured_or_underinsured" and insured:
        note = "With insurance, you qualify if your medical bills are high compared with your income."
    hit = _level(prog["levels"], percent) if applies else None
    alt = None
    if applies and prog.get("alt"):
        alt_hit = _level(prog["alt"][1], percent)
        if alt_hit:
            alt = (prog["alt"][0], alt_hit[0])
    return dict(name=prog["name"], summary=prog["summary"], applies=applies, note=note,
                off=hit[0] if hit else None, covered=hit is not None, alt=alt,
                monthly_cap_pct=prog.get("monthly_cap_pct"), deadline=prog.get("deadline"),
                source=prog.get("source") or STATE_TABLE_SOURCE)


def check(household: int, income: Decimal, state: str | None, insured: bool | None = None,
          amount: Decimal | None = None, hospital: str | None = None, date_of_service: str | None = None) -> dict:
    state = (state or "").upper() or None
    line = poverty_line(household, state)
    percent = int((income / Decimal(line) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    people = f"{household} {'person' if household == 1 else 'people'}"
    where = STATE_NAMES.get(state, "your state")
    st = _state_result(state, percent, insured)
    amount = amount if amount and amount > 0 else None

    # ---- the main result: state law first (a guarantee), then what most hospitals' own policies give ----
    off = None                 # % taken off the bill, when known
    guaranteed = False         # True when the state's law (not just hospital policy) covers this income
    if st and st["covered"]:
        guaranteed = True
        off = st["off"]
        if off == 100:
            tier, headline = "free", f"You may qualify for free hospital care under {st['name']}"
        elif off:
            tier, headline = "discount", f"You may qualify to pay only {100 - off}% of your hospital bill"
        else:
            tier, headline = "discount", f"You may qualify for a discount under {st['name']}"
    elif percent <= 200:
        tier, headline = "free", "You may qualify for free or nearly free hospital care"
    elif percent <= 400:
        tier, headline = "discount", "You may qualify for a discount on your hospital bill"
    else:
        tier, headline = "ask", "You can still lower this bill"

    # ---- Medicaid ----
    medicaid = None
    if percent <= MEDICAID_ADULT_LIMIT:
        if state in MEDICAID_NOT_EXPANDED:
            medicaid = dict(likely=False, text=(
                f"Medicaid for adults is limited in {where}, but children, pregnant people, people over 65 and "
                f"people with disabilities may still qualify. Ask the hospital to check."))
        else:
            medicaid = dict(likely=True, text=(
                f"At your income, adults can usually get Medicaid in {where}. Medicaid can also pay medical bills "
                f"from up to 3 months before you apply (this window gets shorter starting in 2027), so it may "
                f"cover this bill."))
            tier, headline = "free", "You may qualify for Medicaid or free hospital care"

    # ---- what that means in dollars ----
    savings = None
    if amount:
        if tier == "free" and (guaranteed or (medicaid and medicaid["likely"])):
            savings = dict(asked=amount, may_pay=Decimal("0.00"),
                           text=f"You could pay $0 instead of {_money(amount)}.")
        elif tier == "free":
            savings = dict(asked=amount, may_pay=Decimal("0.00"),
                           text=f"If the hospital's policy covers you, you could pay $0 instead of {_money(amount)}.")
        elif off:
            pay = (amount * Decimal(100 - off) / 100).quantize(Decimal("0.01"))
            savings = dict(asked=amount, may_pay=pay,
                           text=f"You may pay about {_money(pay)} instead of {_money(amount)} (save {_money(amount - pay)}).")
        elif tier == "discount" and guaranteed:
            savings = dict(asked=amount, may_pay=None,
                           text=f"{st['name']} limits what the hospital can charge you, often far below {_money(amount)}.")
        elif tier == "discount":
            savings = dict(asked=amount, may_pay=None,
                           text=(f"If you qualify, a nonprofit hospital can't charge you more than what insured "
                                 f"patients pay for the same care, which is often much less than {_money(amount)}."))
        else:
            savings = dict(asked=amount, may_pay=None,
                           text=f"Ask for a discount and a no-interest payment plan for the {_money(amount)}.")

    # ---- payment plan ----
    monthly_income = income / 12
    plan = None
    if st and st["applies"] and st["monthly_cap_pct"] and st["covered"]:
        cap = (monthly_income * st["monthly_cap_pct"] / 100).quantize(Decimal("1"))
        plan = dict(monthly=cap, legal_cap=True,
                    text=f"By {where} law, monthly payments can't be more than {_money(cap)} "
                         f"({st['monthly_cap_pct']}% of your monthly income).")
    elif tier != "free" and income > 0:
        cap = (monthly_income * SUGGESTED_PLAN_PCT / 100).quantize(Decimal("1"))
        owed = savings["may_pay"] if savings and savings["may_pay"] is not None else amount
        months = math.ceil(owed / cap) if owed and cap > 0 else None
        plan = None if months == 1 else dict(monthly=cap, legal_cap=False,
                    text=(f"If you still owe something, ask for an interest-free plan of about {_money(cap)} a month "
                          f"({SUGGESTED_PLAN_PCT}% of your monthly income)"
                          + (f", which would pay off {_money(owed)} in about {months} month{'s' if months > 1 else ''}."
                             if months else ".")))

    # ---- details shown under the headline ----
    details = [f"Your household income is about {percent}% of the {GUIDELINE_YEAR} federal poverty guideline "
               f"(${line:,} for {people})."]
    if st:
        if st["covered"] and st["off"] not in (None, 100):
            details.append(f"Under {st['name']}, your income gets {st['off']}% off the hospital bill.")
        if st["alt"]:
            label, alt_off = st["alt"]
            details.append(f"{label}, the rule is even better for you: "
                           + ("free care." if alt_off == 100 else f"{alt_off}% off." if alt_off else "a discount."))
        if st["applies"] and not st["covered"] and st["off"] is None and STATE_PROGRAMS[state]["levels"]:
            details.append(f"Your income is above the limit of {st['name']}, but hospitals' own policies may still help.")
    if tier == "free" and not guaranteed and not (medicaid and medicaid["likely"]):
        details.append("Most nonprofit hospitals give free care up to about 200% of the guideline, but each hospital "
                       "sets its own limits.")
    elif tier == "discount" and not guaranteed:
        details.append("Many hospitals give discounts up to 300% to 400% of the guideline. Each sets its own limits.")
    elif tier == "ask":
        details.append("Your income is above most hospitals' assistance limits, but bills can still be lowered: "
                       "hospitals often discount for paying in full, and most offer payment plans with no interest.")
    if insured is not False and tier != "ask":
        details.append("Having insurance doesn't stop you from applying: assistance can cover what insurance didn't pay.")

    # ---- your rights (federal rules for nonprofit hospitals, IRS 501(r)) ----
    rights = [
        "Once you qualify, a nonprofit hospital can't charge you more than it gets from insured patients for the "
        "same care.",
        "If you qualify after already paying, the hospital must refund what you paid above what you owe.",
        "While your application is being reviewed, the hospital must pause collections. It can't take steps like "
        "credit reporting until at least 120 days after your first bill.",
    ]

    # ---- next steps ----
    if tier == "ask":
        steps = [
            "Ask for an itemized bill and check every charge with Candorify.",
            "Ask if they give a discount for paying in full or for self-pay patients.",
            "Ask for an interest-free payment plan you can afford.",
            "If you have insurance, check whether you've reached your out-of-pocket maximum for the year. If so, "
            "you may owe less.",
            "If your medical bills are large compared with your income, apply for financial assistance anyway: "
            "some hospitals look at hardship, not just income.",
        ]
    else:
        steps = ["Ask the billing office for its Financial Assistance Policy and application. Nonprofit hospitals "
                 "must give them for free and post them online."]
        if medicaid and medicaid["likely"]:
            steps.append("Ask to be screened for Medicaid. If you qualify, it can pay this bill.")
        if st and st["applies"] and st["covered"]:
            steps.append(f"Ask to be screened for help under the {st['name']}.")
            steps += [
            "Ask them to put your bill on hold and pause collections while you apply.",
            "Gather proof of income for everyone in your household: recent pay stubs, a tax return, or a benefits "
            "letter (like SNAP).",
            "Send your application with the letter below, keep a copy, and write down the date and who you spoke with.",
        ]

    deadline = (st["deadline"] if st and st["deadline"] else None) or FEDERAL_DEADLINE
    subject, letter = _letter(tier, st, medicaid, amount, plan, hospital, date_of_service)
    state_out = None
    if st:
        state_out = dict(name=st["name"], summary=st["summary"], applies=st["applies"], note=st["note"],
                         source=st["source"])
    return {
        "guideline_year": GUIDELINE_YEAR, "poverty_line": line, "percent_of_poverty": percent, "state": state,
        "tier": tier, "headline": headline, "guaranteed": guaranteed,
        "savings": savings, "medicaid": medicaid, "state_program": state_out, "payment_plan": plan,
        "details": details, "rights": rights, "next_steps": steps, "deadline": deadline,
        "letter_subject": subject, "letter": letter, "more_info": STATE_TABLE_SOURCE,
    }


def _letter(tier, st, medicaid, amount, plan, hospital, date_of_service) -> tuple[str, str]:
    to = f"Dear {hospital.strip()} Billing Office," if hospital and hospital.strip() else "Dear Billing Office,"
    visit = f"date of service: {date_of_service.strip()}" if date_of_service and date_of_service.strip() \
        else "date of service: [date]"
    balance = f", with a balance of {_money(amount)}" if amount else ""
    sign = "Thank you,\n[Your name]\n[Your email or phone]"
    if tier == "ask":
        plan_line = f"about {_money(plan['monthly'])} per month" if plan else "an amount I can afford each month"
        return ("Request for a discount and payment plan", (
            f"{to}\n\n"
            f"I am writing about my bill (account number: [your account number], {visit}){balance}. "
            "I want to resolve this bill and am asking for help to make it affordable.\n\n"
            "Please send me or offer:\n"
            "1. An itemized bill showing each charge.\n"
            "2. Any discount you give for paying in full or for self-pay patients.\n"
            f"3. An interest-free payment plan of {plan_line}.\n"
            "4. A copy of your Financial Assistance Policy, in case I qualify.\n\n"
            "Please place my account on hold and pause any collection activity while we agree on this.\n\n"
            f"{sign}"))
    extra = ""
    if st and st["applies"] and st["covered"]:
        extra += f"I am also asking to be screened for assistance under the {st['name']}.\n"
    if medicaid and medicaid["likely"]:
        extra += "Please also screen me for Medicaid, which may cover this bill.\n"
    return ("Financial assistance application", (
        f"{to}\n\n"
        f"I am writing about my bill (account number: [your account number], {visit}){balance}. "
        "I would like to apply for financial assistance under your Financial Assistance Policy.\n"
        + (f"\n{extra}" if extra else "") +
        "\nPlease send me:\n"
        "1. A copy of your Financial Assistance Policy and its plain-language summary.\n"
        "2. The application form and the list of documents you need.\n\n"
        "Please place my account on hold and pause any collection activity while my application is reviewed. "
        "If I qualify, please limit my bill to the amount allowed under your policy and refund anything I have "
        "already paid above that amount.\n\n"
        f"{sign}"))