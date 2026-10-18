"""Offline table of common codes, used when NLM is unavailable or doesn't cover the code.
NLM has HCPCS and ICD-10-CM only; CPT codes (licensed by the AMA) and hospital revenue codes
are not in NLM, so for those this table is the main source.

Each entry: code -> (system, description, plain_english)
"""

FALLBACK_CODES: dict[str, tuple[str, str, str]] = {
    # ---- CPT: emergency department visits ----
    "99281": ("CPT", "Emergency department visit, level 1", "Emergency room visit, level 1 of 5 (the simplest kind)"),
    "99282": ("CPT", "Emergency department visit, level 2", "Emergency room visit, level 2 of 5 (low complexity)"),
    "99283": ("CPT", "Emergency department visit, level 3", "Emergency room visit, level 3 of 5 (moderate complexity)"),
    "99284": ("CPT", "Emergency department visit, level 4", "Emergency room visit, level 4 of 5 (moderately high complexity)"),
    "99285": ("CPT", "Emergency department visit, level 5", "Emergency room visit, level 5 of 5 (the most complex kind)"),
    # ---- CPT: office visits ----
    "99202": ("CPT", "Office visit, new patient, level 2", "Doctor's office visit as a new patient (short, straightforward)"),
    "99203": ("CPT", "Office visit, new patient, level 3", "Doctor's office visit as a new patient (low complexity)"),
    "99204": ("CPT", "Office visit, new patient, level 4", "Doctor's office visit as a new patient (moderate complexity)"),
    "99205": ("CPT", "Office visit, new patient, level 5", "Doctor's office visit as a new patient (high complexity)"),
    "99211": ("CPT", "Office visit, established patient, level 1", "Brief office visit, often with a nurse"),
    "99212": ("CPT", "Office visit, established patient, level 2", "Doctor's office visit, returning patient (straightforward)"),
    "99213": ("CPT", "Office visit, established patient, level 3", "Doctor's office visit, returning patient (low complexity)"),
    "99214": ("CPT", "Office visit, established patient, level 4", "Doctor's office visit, returning patient (moderate complexity)"),
    "99215": ("CPT", "Office visit, established patient, level 5", "Doctor's office visit, returning patient (high complexity)"),
    # ---- CPT: imaging ----
    "71046": ("CPT", "Chest X-ray, two views", "Chest X-ray with two pictures (front and side)"),
    "74177": ("CPT", "CT scan, abdomen and pelvis, with contrast", "CT scan of the belly and pelvis, using contrast dye"),
    # ---- CPT: lab tests ----
    "80048": ("CPT", "Basic metabolic panel", "Blood test for kidney function, blood sugar and electrolytes"),
    "80053": ("CPT", "Comprehensive metabolic panel", "Blood test for kidney and liver function, blood sugar and electrolytes"),
    "85025": ("CPT", "Complete blood count with automated differential", "Blood test counting red cells, white cells (by type) and platelets"),
    "36415": ("CPT", "Routine venipuncture", "Drawing blood from a vein"),
    # ---- CPT: procedures / tests ----
    "93000": ("CPT", "Electrocardiogram with interpretation and report", "Heart rhythm test (ECG/EKG), including the doctor's reading"),
    "94760": ("CPT", "Pulse oximetry, single determination", "One-time check of the oxygen level in your blood (finger clip)"),
    "96365": ("CPT", "IV infusion, initial, up to 1 hour", "First hour of medicine or fluid given slowly through an IV"),
    "96374": ("CPT", "IV push, single or initial drug", "Medicine injected quickly into an IV"),
    # ---- HCPCS Level II (also in NLM; kept here for offline use) ----
    "A6402": ("HCPCS", "Gauze, non-impregnated, sterile, pad size 16 sq. in. or less, without adhesive border, each dressing",
              "Sterile gauze bandage pad"),
    "J0696": ("HCPCS", "Injection, ceftriaxone sodium, per 250 mg", "Antibiotic shot (ceftriaxone), billed per 250 mg"),
    "J1885": ("HCPCS", "Injection, ketorolac tromethamine, per 15 mg", "Pain-relief shot (ketorolac / Toradol), billed per 15 mg"),
    "J2405": ("HCPCS", "Injection, ondansetron hydrochloride, per 1 mg", "Anti-nausea shot (ondansetron / Zofran), billed per 1 mg"),
    "J7030": ("HCPCS", "Infusion, normal saline solution, 1000 cc", "One liter bag of salt-water IV fluid"),
    # ---- Hospital revenue codes (department / category of charge) ----
    "0250": ("Revenue code", "Pharmacy, general", "Medicines and pharmacy supplies"),
    "0270": ("Revenue code", "Medical/surgical supplies, general", "Medical and surgical supplies"),
    "0300": ("Revenue code", "Laboratory, general", "Lab tests"),
    "0320": ("Revenue code", "Radiology, diagnostic, general", "X-rays and other imaging"),
    "0350": ("Revenue code", "CT scan, general", "CT scan charges"),
    "0360": ("Revenue code", "Operating room services, general", "Operating room charges"),
    "0450": ("Revenue code", "Emergency room, general", "Emergency room facility charge"),
    "0636": ("Revenue code", "Drugs requiring detailed coding", "Medicines that must be listed with a specific drug code"),
    "0710": ("Revenue code", "Recovery room, general", "Time spent in the recovery room"),
    "0730": ("Revenue code", "EKG/ECG, general", "Heart rhythm test charges"),
}