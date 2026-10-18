"""
knowledge_base.py — small reference dictionaries used by the extraction and
rules engine. In a real product these would be proper, maintained medical
databases; for a college prototype a curated sample is sufficient and keeps
the demo predictable.
"""

# brand/generic name (lowercased) -> active ingredient
# Used for duplicate-ingredient detection (Requirement 12).
#
# COVERAGE NOTE: this is a curated sample of common Indian brand/generic
# names, not a complete drug database — no static dictionary can realistically
# cover the tens of thousands of branded drugs on the market. A name that's
# missing here is NOT treated as "safe/no issue" — extraction.py already
# falls back to an "unrecognised medicine" record (high-severity issue) when
# nothing in this dict matches, so unknown medicines are flagged for human
# verification rather than silently skipped. Extend this list as needed; when
# adding an entry, verify the active ingredient from the strip/box or a
# pharmacy reference (e.g. 1mg, PharmEasy) — a wrong mapping here is worse
# than an unrecognised-medicine flag, since it would feed the duplicate-
# ingredient and quantity checks bad data.
MEDICINE_INGREDIENTS = {
    # --- Pain / fever ---
    "paracetamol": "paracetamol",
    "crocin": "paracetamol",
    "calpol": "paracetamol",
    "dolo": "paracetamol",
    "dolo 650": "paracetamol",
    "tylenol": "paracetamol",
    "acetaminophen": "paracetamol",
    "fepanil": "paracetamol",
    "pyrigesic": "paracetamol",
    "ibuprofen": "ibuprofen",
    "brufen": "ibuprofen",
    "combiflam": "ibuprofen+paracetamol",
    "diclofenac": "diclofenac",
    "voveran": "diclofenac",
    "aceclofenac": "aceclofenac",
    "zerodol": "aceclofenac",
    "mefenamic acid": "mefenamic acid",
    "meftal": "mefenamic acid",
    "meftal-p": "mefenamic acid+paracetamol",
    "meftal spas": "mefenamic acid+dicyclomine",
    "naproxen": "naproxen",
    "etoricoxib": "etoricoxib",
    "etoshine": "etoricoxib",
    "tramadol": "tramadol",

    # --- Antibiotics ---
    "amoxicillin": "amoxicillin",
    "amoxil": "amoxicillin",
    "mox": "amoxicillin",
    "augmentin": "amoxicillin+clavulanic acid",
    "clavam": "amoxicillin+clavulanic acid",
    "azithromycin": "azithromycin",
    "azithral": "azithromycin",
    "azee": "azithromycin",
    "azax": "azithromycin",
    "ciprofloxacin": "ciprofloxacin",
    "ciplox": "ciprofloxacin",
    "levofloxacin": "levofloxacin",
    "levoflox": "levofloxacin",
    "ofloxacin": "ofloxacin",
    "oflox": "ofloxacin",
    "doxycycline": "doxycycline",
    "doxt": "doxycycline",
    "cefixime": "cefixime",
    "taxim-o": "cefixime",
    "zifi": "cefixime",
    "metronidazole": "metronidazole",
    "flagyl": "metronidazole",
    "metrogyl": "metronidazole",
    "clindamycin": "clindamycin",

    # --- Gastro / antacids ---
    "omeprazole": "omeprazole",
    "omez": "omeprazole",
    "pantoprazole": "pantoprazole",
    "pantocid": "pantoprazole",
    "pan": "pantoprazole",
    "pan-d": "pantoprazole+domperidone",
    "rabeprazole": "rabeprazole",
    "rablet": "rabeprazole",
    "esomeprazole": "esomeprazole",
    "nexpro": "esomeprazole",
    "ranitidine": "ranitidine",
    "domperidone": "domperidone",
    "domstal": "domperidone",
    "ondansetron": "ondansetron",
    "emeset": "ondansetron",

    # --- Allergy / antihistamines ---
    "cetirizine": "cetirizine",
    "cetrizine": "cetirizine",
    "cetzine": "cetirizine",
    "levocetirizine": "levocetirizine",
    "levocet": "levocetirizine",
    "fexofenadine": "fexofenadine",
    "allegra": "fexofenadine",
    "montelukast": "montelukast",
    "montair": "montelukast",
    "montek": "montelukast",
    "montek lc": "montelukast+levocetirizine",

    # --- Respiratory / cough-cold ---
    "salbutamol": "salbutamol",
    "asthalin": "salbutamol",
    "levosalbutamol": "levosalbutamol",
    "levolin": "levosalbutamol",
    "ambroxol": "ambroxol",
    "mucolite": "ambroxol",
    "bromhexine": "bromhexine",

    # --- Diabetes ---
    "metformin": "metformin",
    "glycomet": "metformin",
    "glimepiride": "glimepiride",
    "amaryl": "glimepiride",
    "sitagliptin": "sitagliptin",
    "januvia": "sitagliptin",

    # --- Cardiac / blood pressure ---
    "amlodipine": "amlodipine",
    "amlong": "amlodipine",
    "amlopres": "amlodipine",
    "losartan": "losartan",
    "losar": "losartan",
    "telmisartan": "telmisartan",
    "telma": "telmisartan",
    "atorvastatin": "atorvastatin",
    "atorva": "atorvastatin",
    "storvas": "atorvastatin",

    # --- Vitamins / supplements ---
    "vitamin d3": "vitamin d3",
    "calcirol": "vitamin d3",
    "b-complex": "vitamin b complex",
    "neurobion": "vitamin b complex",

    # --- Anticoagulants / antiplatelets (added for interaction checking) ---
    "warfarin": "warfarin",
    "aspirin": "aspirin",
    "ecosprin": "aspirin",
    "clopidogrel": "clopidogrel",
    "clopilet": "clopidogrel",

    # --- Nitrates / PDE5 inhibitors (added for interaction checking) ---
    "sildenafil": "sildenafil",
    "suhagra": "sildenafil",
    "isosorbide": "isosorbide dinitrate",
    "sorbitrate": "isosorbide dinitrate",
    "nitroglycerin": "nitroglycerin",

    # --- Sulfa antibiotics (added for allergy cross-reference) ---
    "cotrimoxazole": "sulfamethoxazole+trimethoprim",
    "bactrim": "sulfamethoxazole+trimethoprim",
    "septran": "sulfamethoxazole+trimethoprim",

    # --- Added for look-alike/sound-alike (LASA) confusion detection ---
    # These are clinically distinct drugs whose NAMES are frequently
    # misread/mis-transcribed for one another. They must be individually
    # recognisable here (not merged with an existing entry) so the LASA
    # fuzzy-matcher in rules_engine.check_lasa_confusion() can tell them
    # apart. See LASA_PAIRS below for the actual confusion pairs.
    "amiodarone": "amiodarone",
    "hydroxyzine": "hydroxyzine",
    "atarax": "hydroxyzine",
    "hydralazine": "hydralazine",
    "loratadine": "loratadine",
    "prednisone": "prednisone",
    "prednisolone": "prednisolone",
    "omnacortil": "prednisolone",
    "clonidine": "clonidine",
    "cefpodoxime": "cefpodoxime",
    "erythromycin": "erythromycin",
}

# ---------------------------------------------------------------------------
# Look-alike / sound-alike (LASA) drug name confusion pairs.
#
# Unlike everything else in this file, this is NOT about active ingredients
# or clinical effects — it is purely about NAME SIMILARITY between two
# clinically unrelated drugs that are well-documented sources of real-world
# prescribing/dispensing errors (a category tracked by organisations like
# ISMP — the Institute for Safe Medication Practices). A misread of one for
# the other is exactly the kind of error handwriting OCR is prone to, and is
# NOT caught by exact-name matching, duplicate-ingredient checking, or any
# interaction table, because the two drugs share no ingredient and may not
# even be prescribed together.
#
# Keys are frozensets of two entries from MEDICINE_INGREDIENTS (lowercase
# generic names). Used by rules_engine.check_lasa_confusion(), which fuzzy-
# matches raw prescription text against the full medicine name list and
# raises a flag when a single ambiguous word is close enough in spelling to
# match BOTH members of a known pair.
#
# COVERAGE NOTE: same caveat as the other reference dicts in this file — a
# small curated sample of well-known LASA pairs, not an exhaustive list (real
# LASA reference lists run into the hundreds of pairs). A pair missing here
# is simply not checked, not treated as "safe to confuse".
LASA_PAIRS = {
    frozenset({"amlodipine", "amiodarone"}): (
        "Amlodipine (a blood-pressure medicine) and Amiodarone (a heart-rhythm "
        "medicine) are dosed very differently and treat different problems — "
        "confusing one for the other is a well-documented prescribing error."
    ),
    frozenset({"hydroxyzine", "hydralazine"}): (
        "Hydroxyzine (an antihistamine/anti-anxiety medicine) and Hydralazine "
        "(a blood-pressure medicine) are frequently confused due to similar "
        "spelling, despite treating completely different conditions."
    ),
    frozenset({"losartan", "loratadine"}): (
        "Losartan (a blood-pressure medicine) and Loratadine (an allergy "
        "medicine) are commonly confused due to similar spelling."
    ),
    frozenset({"prednisone", "prednisolone"}): (
        "Prednisone and Prednisolone are both steroids but are not always "
        "interchangeable at the same dose, and mix-ups between the two are "
        "a recognised source of dosing errors."
    ),
    frozenset({"metformin", "metronidazole"}): (
        "Metformin (a diabetes medicine) and Metronidazole (an antibiotic) "
        "are dosed and used completely differently despite similar spelling."
    ),
    frozenset({"clopidogrel", "clonidine"}): (
        "Clopidogrel (a blood-thinning medicine) and Clonidine (a blood-"
        "pressure medicine) are frequently confused due to similar spelling, "
        "despite very different effects and risks."
    ),
    frozenset({"cefixime", "cefpodoxime"}): (
        "Cefixime and Cefpodoxime are both cephalosporin antibiotics with "
        "similar names but different dosing — confusing one for the other "
        "can lead to an incorrect dose."
    ),
    frozenset({"azithromycin", "erythromycin"}): (
        "Azithromycin and Erythromycin are both macrolide antibiotics with "
        "similar-sounding names but different dosing schedules."
    ),
}

# ---------------------------------------------------------------------------
# Maximum safe cumulative daily dose (mg/day), used for cross-prescription
# overdose-risk tracking (Feature: cumulative dose tracking).
#
# This checks something a single-prescription duplicate-ingredient check
# CANNOT: the same active ingredient arriving from multiple sources (e.g.
# plain Paracetamol from one doctor + Dolo 650 from another) whose combined
# daily total crosses a genuinely unsafe threshold, even though no single
# prescription looks wrong on its own.
#
# Keys MUST be single active-ingredient tokens exactly as they appear in
# MEDICINE_INGREDIENTS values (combination drugs are split on "+" before
# lookup — see rules_engine.check_cumulative_dose). Values are commonly-
# cited adult maximum daily doses in mg.
#
# COVERAGE NOTE: same caveat as the rest of this file — a curated sample for
# a college prototype, not a substitute for individualised dosing guidance
# from a doctor/pharmacist (safe limits vary by age, weight, kidney/liver
# function, and other medicines). An ingredient missing here is NOT treated
# as "safe at any dose" — it is simply not checked by this specific feature.
MAX_SAFE_DAILY_DOSE_MG = {
    "paracetamol": 4000,
    "ibuprofen": 2400,
    "diclofenac": 150,
    "aceclofenac": 200,
    "naproxen": 1500,
    "mefenamic acid": 1500,
    "metformin": 2550,
    "azithromycin": 500,       # typical short-course single daily dose
    "amoxicillin": 3000,
    "doxycycline": 200,
    "cetirizine": 10,
    "levocetirizine": 5,
    "atorvastatin": 80,
    "metronidazole": 2250,
}

# ---------------------------------------------------------------------------
# Drug–drug interaction pairs (Feature: multi-prescription interaction check).
#
# COVERAGE NOTE: same caveat as MEDICINE_INGREDIENTS above — this is a small,
# curated sample of well-documented interactions for a college prototype, NOT
# a substitute for a real clinical drug-interaction database (e.g. Micromedex,
# Lexicomp). A pair that's missing here is NOT treated as "safe" — it's simply
# not checked. Keys are frozensets of two single active-ingredient tokens
# (combination drugs like "ibuprofen+paracetamol" are split on "+" before
# lookup — see rules_engine.find_drug_interactions). Severity is always
# surfaced as a verification-required alert; this module never tells a
# patient to stop or start a medicine on its own.
DRUG_INTERACTIONS = {
    # Anticoagulant / antiplatelet + NSAID → bleeding risk
    frozenset({"warfarin", "ibuprofen"}): {"severity": "high", "description": "Combining warfarin with ibuprofen (an NSAID) can significantly increase the risk of serious bleeding."},
    frozenset({"warfarin", "diclofenac"}): {"severity": "high", "description": "Combining warfarin with diclofenac (an NSAID) can significantly increase the risk of serious bleeding."},
    frozenset({"warfarin", "aceclofenac"}): {"severity": "high", "description": "Combining warfarin with aceclofenac (an NSAID) can significantly increase the risk of serious bleeding."},
    frozenset({"warfarin", "mefenamic acid"}): {"severity": "high", "description": "Combining warfarin with mefenamic acid (an NSAID) can significantly increase the risk of serious bleeding."},
    frozenset({"warfarin", "etoricoxib"}): {"severity": "high", "description": "Combining warfarin with etoricoxib can increase the risk of bleeding."},
    frozenset({"warfarin", "aspirin"}): {"severity": "high", "description": "Combining warfarin with aspirin substantially increases the risk of serious bleeding."},
    frozenset({"warfarin", "metronidazole"}): {"severity": "high", "description": "Metronidazole can markedly increase warfarin's blood-thinning effect, raising bleeding risk."},
    frozenset({"warfarin", "azithromycin"}): {"severity": "medium", "description": "Azithromycin may increase warfarin's blood-thinning effect (raised INR); bleeding risk should be monitored."},
    frozenset({"warfarin", "ciprofloxacin"}): {"severity": "medium", "description": "Ciprofloxacin may increase warfarin's blood-thinning effect (raised INR); bleeding risk should be monitored."},
    frozenset({"aspirin", "clopidogrel"}): {"severity": "medium", "description": "Aspirin and clopidogrel are both antiplatelet drugs; combined use raises bleeding risk and should only continue under direct medical supervision."},
    frozenset({"clopidogrel", "omeprazole"}): {"severity": "medium", "description": "Omeprazole can reduce clopidogrel's antiplatelet effectiveness, potentially raising clot risk. Pantoprazole/rabeprazole are often preferred alongside clopidogrel."},
    frozenset({"clopidogrel", "esomeprazole"}): {"severity": "medium", "description": "Esomeprazole can reduce clopidogrel's antiplatelet effectiveness, potentially raising clot risk."},

    # Dangerous nitrate + PDE5 inhibitor combination
    frozenset({"sildenafil", "isosorbide dinitrate"}): {"severity": "high", "description": "Sildenafil combined with a nitrate can cause a sudden, severe, potentially life-threatening drop in blood pressure."},
    frozenset({"sildenafil", "nitroglycerin"}): {"severity": "high", "description": "Sildenafil combined with a nitrate can cause a sudden, severe, potentially life-threatening drop in blood pressure."},

    # QT-prolonging combinations
    frozenset({"azithromycin", "domperidone"}): {"severity": "high", "description": "Azithromycin and domperidone can both prolong the heart's QT interval; combined use raises the risk of a dangerous irregular heartbeat."},
    frozenset({"ciprofloxacin", "domperidone"}): {"severity": "high", "description": "Ciprofloxacin and domperidone can both prolong the heart's QT interval; combined use raises the risk of a dangerous irregular heartbeat."},
    frozenset({"levofloxacin", "domperidone"}): {"severity": "high", "description": "Levofloxacin and domperidone can both prolong the heart's QT interval; combined use raises the risk of a dangerous irregular heartbeat."},
    frozenset({"ciprofloxacin", "ondansetron"}): {"severity": "high", "description": "Ciprofloxacin and ondansetron can both prolong the heart's QT interval; combined use raises the risk of a dangerous irregular heartbeat."},
    frozenset({"levofloxacin", "ondansetron"}): {"severity": "high", "description": "Levofloxacin and ondansetron can both prolong the heart's QT interval; combined use raises the risk of a dangerous irregular heartbeat."},

    # Serotonergic combination
    frozenset({"tramadol", "ondansetron"}): {"severity": "high", "description": "Tramadol and ondansetron both increase serotonin activity; combined use raises the risk of serotonin syndrome (agitation, high fever, rapid heartbeat)."},

    # Duplicate/overlapping NSAID use (different drugs, same risk class)
    frozenset({"ibuprofen", "diclofenac"}): {"severity": "high", "description": "Taking two different NSAIDs together does not add benefit and increases the risk of stomach ulcers and bleeding."},
    frozenset({"ibuprofen", "aceclofenac"}): {"severity": "high", "description": "Taking two different NSAIDs together does not add benefit and increases the risk of stomach ulcers and bleeding."},
    frozenset({"ibuprofen", "mefenamic acid"}): {"severity": "high", "description": "Taking two different NSAIDs together does not add benefit and increases the risk of stomach ulcers and bleeding."},
    frozenset({"diclofenac", "aceclofenac"}): {"severity": "high", "description": "Taking two different NSAIDs together does not add benefit and increases the risk of stomach ulcers and bleeding."},
    frozenset({"diclofenac", "mefenamic acid"}): {"severity": "high", "description": "Taking two different NSAIDs together does not add benefit and increases the risk of stomach ulcers and bleeding."},
    frozenset({"aceclofenac", "mefenamic acid"}): {"severity": "high", "description": "Taking two different NSAIDs together does not add benefit and increases the risk of stomach ulcers and bleeding."},
    frozenset({"ibuprofen", "etoricoxib"}): {"severity": "medium", "description": "Combining two anti-inflammatory drugs from overlapping classes increases the risk of stomach and kidney side effects."},

    # NSAID + antihypertensive
    frozenset({"ibuprofen", "amlodipine"}): {"severity": "medium", "description": "NSAIDs like ibuprofen can reduce the blood-pressure-lowering effect of amlodipine and add strain on the kidneys."},
    frozenset({"diclofenac", "amlodipine"}): {"severity": "medium", "description": "NSAIDs like diclofenac can reduce the blood-pressure-lowering effect of amlodipine and add strain on the kidneys."},
    frozenset({"aceclofenac", "losartan"}): {"severity": "medium", "description": "NSAIDs can reduce the effectiveness of losartan and increase the risk of kidney injury, especially if dehydrated."},
    frozenset({"ibuprofen", "losartan"}): {"severity": "medium", "description": "NSAIDs can reduce the effectiveness of losartan and increase the risk of kidney injury, especially if dehydrated."},
    frozenset({"mefenamic acid", "telmisartan"}): {"severity": "medium", "description": "NSAIDs can reduce the effectiveness of telmisartan and increase the risk of kidney injury, especially if dehydrated."},

    # NSAID + metformin (renal clearance concern)
    frozenset({"ibuprofen", "metformin"}): {"severity": "medium", "description": "NSAIDs may affect kidney function, which can in turn affect how metformin is cleared from the body."},

    # Sulfonylurea + fluoroquinolone (hypoglycemia risk)
    frozenset({"glimepiride", "ciprofloxacin"}): {"severity": "medium", "description": "Fluoroquinolones like ciprofloxacin can enhance the blood-sugar-lowering effect of glimepiride, raising the risk of hypoglycemia."},
    frozenset({"glimepiride", "levofloxacin"}): {"severity": "medium", "description": "Fluoroquinolones like levofloxacin can enhance the blood-sugar-lowering effect of glimepiride, raising the risk of hypoglycemia."},
}

# ---------------------------------------------------------------------------
# Allergy cross-reference (Feature: allergy-based medicine alert).
#
# Maps a general allergy term a patient might record (drug class, chemical
# family) to the specific active-ingredient tokens in MEDICINE_INGREDIENTS
# that a person with that allergy should also avoid. This is IN ADDITION to
# a direct substring match of the recorded allergy text against a medicine's
# name/active ingredient (handled in rules_engine.check_allergy_conflicts) —
# so a patient who typed "amoxicillin" is already covered without needing an
# entry here; this dict exists for indirect/class-level allergy statements
# like "penicillin" or "sulfa drugs".
#
# COVERAGE NOTE: curated sample only, not a complete allergen/cross-
# reactivity reference. Keys should be lowercase.
ALLERGY_CROSS_REFERENCE = {
    "penicillin": ["amoxicillin"],
    "penicillins": ["amoxicillin"],
    "sulfa": ["sulfamethoxazole"],
    "sulfa drugs": ["sulfamethoxazole"],
    "sulfonamide": ["sulfamethoxazole"],
    "sulfonamides": ["sulfamethoxazole"],
    "nsaid": ["ibuprofen", "diclofenac", "aceclofenac", "mefenamic acid", "naproxen", "etoricoxib", "aspirin"],
    "nsaids": ["ibuprofen", "diclofenac", "aceclofenac", "mefenamic acid", "naproxen", "etoricoxib", "aspirin"],
    "aspirin": ["aspirin", "ibuprofen", "diclofenac", "aceclofenac", "mefenamic acid", "naproxen", "etoricoxib"],
    "quinolone": ["ciprofloxacin", "levofloxacin", "ofloxacin"],
    "quinolones": ["ciprofloxacin", "levofloxacin", "ofloxacin"],
    "fluoroquinolone": ["ciprofloxacin", "levofloxacin", "ofloxacin"],
    "fluoroquinolones": ["ciprofloxacin", "levofloxacin", "ofloxacin"],
    "macrolide": ["azithromycin"],
    "macrolides": ["azithromycin"],
    "cephalosporin": ["cefixime"],
    "cephalosporins": ["cefixime"],
}

# ---------------------------------------------------------------------------
# Disease/condition -> medicine conflict checker (Feature: disease-based
# medicine alert). Works exactly like the allergy checker: the patient
# records a health condition in free text (e.g. "asthma", "kidney disease",
# "high BP"), and every prescription is checked for medicines whose active
# ingredient is known to worsen that condition or reduce its control.
#
# DISEASE_ALIASES normalises the many ways a patient might type a condition
# to one canonical key in DISEASE_MEDICINE_CONFLICTS. Matching in
# rules_engine.check_disease_conflicts is substring-based in both directions,
# so e.g. "I have chronic kidney disease" still matches "kidney disease".
#
# COVERAGE NOTE: same caveat as the other reference dicts in this file — a
# curated sample for a college prototype, not a substitute for a real
# clinical decision-support database. A condition/medicine pair that's
# missing here is NOT treated as "safe" — it's simply not checked, and stays
# the responsibility of the verifying doctor/pharmacist like everything else
# this module flags.
DISEASE_ALIASES = {
    "asthma": "asthma", "bronchial asthma": "asthma", "wheezing": "asthma",

    "kidney disease": "kidney disease", "ckd": "kidney disease",
    "chronic kidney disease": "kidney disease", "renal disease": "kidney disease",
    "renal failure": "kidney disease", "kidney failure": "kidney disease",

    "peptic ulcer": "peptic ulcer", "gastric ulcer": "peptic ulcer",
    "stomach ulcer": "peptic ulcer", "duodenal ulcer": "peptic ulcer",
    "gerd": "peptic ulcer", "acid reflux": "peptic ulcer",

    "hypertension": "hypertension", "high blood pressure": "hypertension",
    "high bp": "hypertension", "bp": "hypertension",

    "liver disease": "liver disease", "hepatic disease": "liver disease",
    "jaundice": "liver disease", "cirrhosis": "liver disease",

    "heart disease": "heart disease", "cardiac disease": "heart disease",
    "heart failure": "heart disease", "cardiovascular disease": "heart disease",

    "diabetes": "diabetes", "diabetic": "diabetes", "sugar": "diabetes",
    "type 2 diabetes": "diabetes", "type 1 diabetes": "diabetes",

    "pregnancy": "pregnancy", "pregnant": "pregnancy",

    "g6pd deficiency": "g6pd deficiency", "g6pd": "g6pd deficiency",

    "epilepsy": "epilepsy", "seizure disorder": "epilepsy", "seizures": "epilepsy",
}

# canonical condition -> list of {ingredient, severity, description}
DISEASE_MEDICINE_CONFLICTS = {
    "asthma": [
        {"ingredient": "ibuprofen", "severity": "medium", "description": "NSAIDs like ibuprofen can trigger bronchospasm (sudden breathing difficulty) in some people with asthma."},
        {"ingredient": "aspirin", "severity": "medium", "description": "Aspirin can trigger bronchospasm in a subset of people with asthma (aspirin-exacerbated respiratory disease)."},
        {"ingredient": "diclofenac", "severity": "medium", "description": "NSAIDs like diclofenac can trigger bronchospasm in some people with asthma."},
        {"ingredient": "aceclofenac", "severity": "medium", "description": "NSAIDs like aceclofenac can trigger bronchospasm in some people with asthma."},
        {"ingredient": "mefenamic acid", "severity": "medium", "description": "NSAIDs like mefenamic acid can trigger bronchospasm in some people with asthma."},
        {"ingredient": "etoricoxib", "severity": "low", "description": "COX-2 inhibitors like etoricoxib carry a smaller but still present risk of triggering asthma symptoms in sensitive patients."},
    ],
    "kidney disease": [
        {"ingredient": "ibuprofen", "severity": "high", "description": "NSAIDs like ibuprofen can reduce blood flow to the kidneys and worsen kidney function."},
        {"ingredient": "diclofenac", "severity": "high", "description": "NSAIDs like diclofenac can reduce blood flow to the kidneys and worsen kidney function."},
        {"ingredient": "aceclofenac", "severity": "high", "description": "NSAIDs like aceclofenac can reduce blood flow to the kidneys and worsen kidney function."},
        {"ingredient": "mefenamic acid", "severity": "high", "description": "NSAIDs like mefenamic acid can reduce blood flow to the kidneys and worsen kidney function."},
        {"ingredient": "naproxen", "severity": "high", "description": "NSAIDs like naproxen can reduce blood flow to the kidneys and worsen kidney function."},
        {"ingredient": "etoricoxib", "severity": "high", "description": "COX-2 inhibitors like etoricoxib can also impair kidney function and are generally avoided in kidney disease."},
        {"ingredient": "metformin", "severity": "medium", "description": "Metformin is cleared by the kidneys; reduced kidney function raises the risk of a rare but serious buildup (lactic acidosis) and often needs a dose adjustment."},
    ],
    "peptic ulcer": [
        {"ingredient": "ibuprofen", "severity": "high", "description": "NSAIDs like ibuprofen irritate the stomach lining and can worsen or reopen a peptic ulcer, or cause bleeding."},
        {"ingredient": "diclofenac", "severity": "high", "description": "NSAIDs like diclofenac irritate the stomach lining and can worsen or reopen a peptic ulcer, or cause bleeding."},
        {"ingredient": "aceclofenac", "severity": "high", "description": "NSAIDs like aceclofenac irritate the stomach lining and can worsen or reopen a peptic ulcer, or cause bleeding."},
        {"ingredient": "mefenamic acid", "severity": "high", "description": "NSAIDs like mefenamic acid irritate the stomach lining and can worsen or reopen a peptic ulcer, or cause bleeding."},
        {"ingredient": "aspirin", "severity": "high", "description": "Aspirin irritates the stomach lining and can worsen or reopen a peptic ulcer, or cause bleeding."},
        {"ingredient": "naproxen", "severity": "high", "description": "NSAIDs like naproxen irritate the stomach lining and can worsen or reopen a peptic ulcer, or cause bleeding."},
    ],
    "hypertension": [
        {"ingredient": "ibuprofen", "severity": "medium", "description": "NSAIDs like ibuprofen can cause fluid retention and raise blood pressure, working against blood-pressure medicines."},
        {"ingredient": "diclofenac", "severity": "medium", "description": "NSAIDs like diclofenac can cause fluid retention and raise blood pressure, working against blood-pressure medicines."},
        {"ingredient": "aceclofenac", "severity": "medium", "description": "NSAIDs like aceclofenac can cause fluid retention and raise blood pressure, working against blood-pressure medicines."},
        {"ingredient": "mefenamic acid", "severity": "medium", "description": "NSAIDs like mefenamic acid can cause fluid retention and raise blood pressure, working against blood-pressure medicines."},
        {"ingredient": "naproxen", "severity": "medium", "description": "NSAIDs like naproxen can cause fluid retention and raise blood pressure, working against blood-pressure medicines."},
    ],
    "liver disease": [
        {"ingredient": "paracetamol", "severity": "high", "description": "Paracetamol is processed by the liver; impaired liver function raises the risk of liver damage, especially at higher or repeated doses."},
        {"ingredient": "metronidazole", "severity": "medium", "description": "Metronidazole is processed by the liver and may need a reduced dose in significant liver disease."},
    ],
    "heart disease": [
        {"ingredient": "ibuprofen", "severity": "medium", "description": "NSAIDs like ibuprofen are linked to a higher risk of heart attack and stroke, and are generally avoided in existing heart disease."},
        {"ingredient": "diclofenac", "severity": "high", "description": "Diclofenac carries one of the higher cardiovascular risks among NSAIDs and is generally avoided in existing heart disease."},
        {"ingredient": "etoricoxib", "severity": "high", "description": "COX-2 inhibitors like etoricoxib carry an increased cardiovascular risk and are generally avoided in existing heart disease."},
    ],
    "diabetes": [
        {"ingredient": "cetirizine", "severity": "low", "description": "Antihistamines are usually fine in diabetes, but any new drowsiness should be watched for if other sedating medicines are also in use."},
    ],
    "pregnancy": [
        {"ingredient": "ibuprofen", "severity": "high", "description": "NSAIDs like ibuprofen are generally avoided in pregnancy (especially the third trimester) due to risks to the baby."},
        {"ingredient": "diclofenac", "severity": "high", "description": "NSAIDs like diclofenac are generally avoided in pregnancy (especially the third trimester) due to risks to the baby."},
        {"ingredient": "aceclofenac", "severity": "high", "description": "NSAIDs like aceclofenac are generally avoided in pregnancy (especially the third trimester) due to risks to the baby."},
        {"ingredient": "mefenamic acid", "severity": "high", "description": "NSAIDs like mefenamic acid are generally avoided in pregnancy (especially the third trimester) due to risks to the baby."},
        {"ingredient": "doxycycline", "severity": "high", "description": "Doxycycline (a tetracycline antibiotic) can affect fetal bone and teeth development and is generally avoided in pregnancy."},
        {"ingredient": "ciprofloxacin", "severity": "medium", "description": "Fluoroquinolones like ciprofloxacin are generally avoided in pregnancy unless clearly necessary."},
        {"ingredient": "levofloxacin", "severity": "medium", "description": "Fluoroquinolones like levofloxacin are generally avoided in pregnancy unless clearly necessary."},
    ],
    "g6pd deficiency": [
        {"ingredient": "ciprofloxacin", "severity": "high", "description": "Ciprofloxacin can trigger red blood cell breakdown (haemolysis) in people with G6PD deficiency."},
        {"ingredient": "sulfamethoxazole+trimethoprim", "severity": "high", "description": "Sulfa antibiotics can trigger red blood cell breakdown (haemolysis) in people with G6PD deficiency."},
    ],
    "epilepsy": [
        {"ingredient": "ciprofloxacin", "severity": "medium", "description": "Fluoroquinolones like ciprofloxacin can lower the seizure threshold in people with epilepsy."},
        {"ingredient": "tramadol", "severity": "medium", "description": "Tramadol can lower the seizure threshold in people with epilepsy."},
    ],
}

# ---------------------------------------------------------------------------
# Generic, rule-level explanation of WHY each issue_type is ever raised —
# used alongside (not instead of) the specific per-instance description
# already produced by rules_engine, so a flagged item can always answer
# "what check triggered this, in general?" as well as "what happened here,
# specifically?" (Feature: explainable "why was this flagged" reasoning).
ISSUE_TYPE_EXPLANATIONS = {
    "unrecognised_medicine": "Triggered when OCR/text extraction could not confidently match any text to a known medicine name — usually illegible handwriting or a name outside the reference list.",
    "low_confidence_name": "Triggered when a medicine name was matched, but the character-level OCR confidence for that name fell below the safe threshold.",
    "missing_field": "Triggered when a medicine is missing its strength/dosage, frequency, or duration — every one of those is needed to take a medicine safely and unambiguously.",
    "abbreviation_detected": "Triggered whenever prescription shorthand (OD, BD, TDS, SOS, etc.) is used — these are automatically expanded, but always flagged since a misread abbreviation changes how often a medicine is taken.",
    "quantity_mismatch": "Triggered when the total quantity written doesn't match dose × frequency × duration — usually a sign one of those numbers was misread, or the prescription itself has an inconsistency.",
    "duplicate_ingredient": "Triggered when two medicines on the same prescription share the same active ingredient — a common cause of accidental double-dosing.",
    "allergy_alert": "Triggered when a medicine's active ingredient matches — directly, or via a known drug-class link — a substance you've recorded as an allergy.",
    "disease_conflict": "Triggered when a medicine's active ingredient is on a list of drugs known to worsen, or interact badly with, a health condition you've recorded.",
    "drug_interaction": "Triggered when the active ingredients of two medicines (possibly from different prescriptions) are a known interacting pair — usually because they affect the same body system or how the body processes the other.",
    "lasa_confusion_risk": "Triggered when a word in the prescription text is close enough in spelling to match TWO different medicines that are a known look-alike/sound-alike (LASA) pair — a common source of real-world dispensing errors, independent of any single ingredient match.",
    "cumulative_overdose_risk": "Triggered when the SAME active ingredient, taken from two or more medicines (possibly different brand names, possibly from different prescriptions/doctors), adds up to more than the generally recognised safe daily total.",
}

# Common prescription-shorthand abbreviations -> plain-English meaning.
# Requirement 10. These are ALWAYS shown with a verification warning —
# the system never silently substitutes them into the "verified" record.
ABBREVIATIONS = {
    "od": "once daily",
    "bd": "twice daily",
    "bid": "twice daily",
    "tds": "three times daily",
    "tid": "three times daily",
    "qid": "four times daily",
    "sos": "as needed (only if required)",
    "hs": "at bedtime",
    "ac": "before food",
    "pc": "after food",
    "stat": "immediately, as a single dose",
    "prn": "as needed",
}

# Numeric "times per day" implied by an abbreviation — used by the
# quantity-consistency checker.
ABBREVIATION_FREQUENCY_COUNT = {
    "od": 1, "bd": 2, "bid": 2, "tds": 3, "tid": 3, "qid": 4,
    "hs": 1, "stat": 1,
}

# English -> Tamil phrase table for the simple-language explanation feature
# (Requirement 20). A static, curated table is used instead of a live
# translation API so the demo works fully offline and predictably.
TRANSLATIONS_TA = {
    "once daily": "நாளொன்றுக்கு ஒரு முறை",
    "twice daily": "நாளொன்றுக்கு இரு முறை",
    "three times daily": "நாளொன்றுக்கு மூன்று முறை",
    "four times daily": "நாளொன்றுக்கு நான்கு முறை",
    "as needed (only if required)": "தேவைப்படும் போது மட்டும்",
    "at bedtime": "படுக்கைக்குச் செல்லும் முன்",
    "before food": "உணவுக்கு முன்",
    "after food": "உணவுக்குப் பிறகு",
    "immediately, as a single dose": "உடனடியாக, ஒரு முறை மட்டும்",
    "as needed": "தேவைப்படும் போது",
    "tablet": "மாத்திரை",
    "tablets": "மாத்திரைகள்",
    "days": "நாட்கள்",
    "take": "எடுத்துக் கொள்ளவும்",
    "for": "மேற்கொண்டு",
    "yes": "ஆம்",
    "no": "இல்லை",
    "alert": "எச்சரிக்கை",
    "no alert": "எச்சரிக்கை இல்லை",
}

# ---------------------------------------------------------------------------
# Medicine name -> Tamil transliteration, for the Tamil-language medicines
# table (Feature: Tamil table view). Keys must match MEDICINE_INGREDIENTS
# keys (lowercase brand/generic name).
#
# COVERAGE NOTE: curated sample only, same caveat as the other reference
# dicts in this file — a medicine name missing here is NOT mistranslated,
# it's shown as-is (see translate_medicine_name_to_tamil below) rather than
# guessed at, since a wrong drug-name transliteration would be genuinely
# dangerous.
MEDICINE_NAMES_TA = {
    "paracetamol": "பாராசிட்டமால்",
    "crocin": "குரோசின்",
    "calpol": "கால்பால்",
    "dolo": "டோலோ",
    "dolo 650": "டோலோ 650",
    "tylenol": "டைலினால்",
    "acetaminophen": "அசிட்டமினோஃபென்",
    "ibuprofen": "ஐபுப்ரூஃபென்",
    "brufen": "புருஃபென்",
    "combiflam": "காம்பிஃப்ளாம்",
    "diclofenac": "டைக்ளோஃபெனாக்",
    "voveran": "வோவரான்",
    "aceclofenac": "அசிக்ளோஃபெனாக்",
    "zerodol": "ஜீரோடால்",
    "mefenamic acid": "மெஃபெனாமிக் அமிலம்",
    "meftal": "மெஃப்டால்",
    "amoxicillin": "அமாக்சிசிலின்",
    "amoxil": "அமாக்சில்",
    "mox": "மாக்ஸ்",
    "augmentin": "ஆக்மென்டின்",
    "azithromycin": "அசித்ரோமைசின்",
    "azithral": "அசித்ரால்",
    "azee": "அசீ",
    "ciprofloxacin": "சிப்ரோஃப்ளாக்சசின்",
    "ciplox": "சிப்லாக்ஸ்",
    "levofloxacin": "லெவோஃப்ளாக்சசின்",
    "doxycycline": "டாக்ஸிசைக்ளின்",
    "cefixime": "செஃபிக்ஸிம்",
    "metronidazole": "மெட்ரோனிடசோல்",
    "flagyl": "ஃப்ளாஜில்",
    "omeprazole": "ஓமீப்ரசோல்",
    "omez": "ஓமெஸ்",
    "pantoprazole": "பான்டோபிரசோல்",
    "pan": "பான்",
    "rabeprazole": "ரபிபிரசோல்",
    "domperidone": "டாம்பெரிடோன்",
    "domstal": "டாம்ஸ்டால்",
    "ondansetron": "ஆன்டான்செட்ரான்",
    "cetirizine": "செட்ரிசின்",
    "cetzine": "செட்ஸின்",
    "levocetirizine": "லெவோசெட்ரிசின்",
    "fexofenadine": "ஃபெக்ஸோஃபெனடின்",
    "allegra": "அலெக்ரா",
    "montelukast": "மான்டேலுகாஸ்ட்",
    "montair": "மான்டேர்",
    "montek": "மான்டெக்",
    "salbutamol": "சால்புடமால்",
    "asthalin": "அஸ்தாலின்",
    "ambroxol": "ஆம்ப்ராக்ஸால்",
    "metformin": "மெட்ஃபார்மின்",
    "glycomet": "கிளைகோமெட்",
    "glimepiride": "க்ளிமெபிரைடு",
    "amlodipine": "அம்லோடிபின்",
    "losartan": "லோசார்டான்",
    "telmisartan": "டெல்மிசார்டான்",
    "atorvastatin": "அடோர்வாஸ்டாடின்",
    "vitamin d3": "வைட்டமின் டி3",
    "b-complex": "பி-காம்ப்ளக்ஸ்",
    "warfarin": "வார்ஃபரின்",
    "aspirin": "ஆஸ்பிரின்",
    "ecosprin": "எக்கோஸ்ப்ரின்",
    "clopidogrel": "க்ளோபிடோகிரல்",
    "sildenafil": "சில்டெனாஃபில்",
}


def translate_phrase_to_tamil(phrase: str) -> str:
    """Best-effort phrase-table translation. Falls back to English with a
    note if no entry exists, rather than guessing."""
    key = phrase.strip().lower()
    if key in TRANSLATIONS_TA:
        return TRANSLATIONS_TA[key]
    return phrase + " (தமிழ் மொழிபெயர்ப்பு கிடைக்கவில்லை)"


def translate_medicine_name_to_tamil(name: str) -> str:
    """Transliterates a medicine name for the Tamil table view. Deliberately
    conservative: only names in MEDICINE_NAMES_TA are translated — anything
    else is returned unchanged rather than guessed, since a wrong drug-name
    transliteration is a genuine safety risk, not just a display glitch."""
    if not name:
        return name
    key = name.strip().lower()
    return MEDICINE_NAMES_TA.get(key, name)


def translate_dosage_to_tamil(dosage: str) -> str:
    """Translates a simple '<number> <unit>' dosage string (e.g. '1 tablet',
    '2 tablets') using the TRANSLATIONS_TA phrase table. Falls back to the
    original text unchanged if it doesn't match that pattern or the unit
    word isn't in the phrase table."""
    if not dosage:
        return dosage
    parts = dosage.strip().split(None, 1)
    if len(parts) == 2 and parts[0].replace(".", "", 1).isdigit():
        number, unit = parts
        unit_ta = TRANSLATIONS_TA.get(unit.strip().lower())
        if unit_ta:
            return f"{number} {unit_ta}"
    return dosage