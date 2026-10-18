"""
rules_engine.py — Stages 4 & 5 of the AI pipeline:
  Stage 4: confidence analysis
  Stage 5: rule-based consistency engine (missing fields, duplicate
           ingredients, quantity mismatch, contradictions)

STRICT RULE: this module only ever FLAGS problems. It never edits, guesses,
or fills in a medicine's fields. All corrections happen later, by a human
verifier, in verification.py / the verifier dashboard.
"""
import re
import difflib
from collections import defaultdict
from knowledge_base import (ABBREVIATION_FREQUENCY_COUNT, DRUG_INTERACTIONS, ALLERGY_CROSS_REFERENCE,
                             DISEASE_ALIASES, DISEASE_MEDICINE_CONFLICTS, MEDICINE_INGREDIENTS,
                             LASA_PAIRS, MAX_SAFE_DAILY_DOSE_MG)

LOW_CONF_THRESHOLD = 60
MED_CONF_THRESHOLD = 85

# Weight used when turning a prescription's open issues into a single
# sortable risk score (see compute_risk_score below).
SEVERITY_WEIGHT = {"high": 3, "medium": 2, "low": 1}


def confidence_band(conf):
    if conf is None:
        return "red"
    if conf >= MED_CONF_THRESHOLD:
        return "green"
    if conf >= LOW_CONF_THRESHOLD:
        return "yellow"
    return "red"


def _duration_to_days(duration_str):
    if not duration_str:
        return None
    m = re.match(r"(\d+)\s*(day|days|week|weeks)", duration_str, re.I)
    if not m:
        return None
    n = int(m.group(1))
    return n * 7 if "week" in m.group(2).lower() else n


def _frequency_to_per_day(freq_raw):
    if not freq_raw:
        return None
    freq_raw = freq_raw.lower().strip()
    if freq_raw in ABBREVIATION_FREQUENCY_COUNT:
        return ABBREVIATION_FREQUENCY_COUNT[freq_raw]
    m = re.match(r"(\d)-(\d)-(\d)", freq_raw)
    if m:
        return sum(1 for g in m.groups() if g != "0")
    return None


def analyse_prescription(medicines):
    """
    medicines: list of dicts from extraction.extract_structured_fields()
    Returns: (issues: list[dict], completeness_score: int, overall_confidence: float)
    Each issue: {issue_type, description, severity, confidence, medicine_index}
    """
    issues = []

    # ---- per-medicine checks ----
    for idx, med in enumerate(medicines):
        conf = med.get("confidence") or 0
        name_conf = med.get("name_confidence") or 0

        # 1. Ambiguity detection on medicine name / handwriting
        if med["name"] is None:
            issues.append({
                "medicine_index": idx, "issue_type": "unrecognised_medicine",
                "description": "Medicine name could not be confidently identified from the text/handwriting.",
                "severity": "high", "confidence": conf,
            })
        elif name_conf < LOW_CONF_THRESHOLD:
            issues.append({
                "medicine_index": idx, "issue_type": "low_confidence_name",
                "description": f"Medicine name '{med['name']}' has low OCR confidence ({name_conf}%). Please verify against the original image.",
                "severity": "medium", "confidence": name_conf,
            })

        # 2. Missing-information detection (Requirement 11)
        missing = []
        if not med.get("dosage") and not med.get("strength"):
            missing.append("dosage/strength")
        if not med.get("frequency"):
            missing.append("frequency")
        if not med.get("duration"):
            missing.append("duration")
        if missing:
            issues.append({
                "medicine_index": idx, "issue_type": "missing_field",
                "description": f"Missing field(s) for {med['name'] or 'this medicine'}: {', '.join(missing)}.",
                "severity": "medium" if len(missing) < 3 else "high",
                "confidence": conf,
            })

        # 3. Abbreviation flag (Requirement 10) — informational, always flagged for verification
        if med.get("frequency") and med["frequency"].lower() in ABBREVIATION_FREQUENCY_COUNT:
            issues.append({
                "medicine_index": idx, "issue_type": "abbreviation_detected",
                "description": f"Abbreviation '{med['frequency'].upper()}' detected → interpreted as '{med.get('frequency_expanded')}'. This interpretation should be verified.",
                "severity": "low", "confidence": 70.0,
            })

        # 4. Quantity / dosage consistency checker (Requirement 13)
        freq_per_day = _frequency_to_per_day(med.get("frequency"))
        duration_days = _duration_to_days(med.get("duration"))
        quantity = med.get("quantity")
        if freq_per_day and duration_days and quantity:
            expected = 1 * freq_per_day * duration_days  # assumes 1 unit/dose
            try:
                written = int(quantity)
            except (TypeError, ValueError):
                written = None
            if written is not None and written != expected:
                issues.append({
                    "medicine_index": idx, "issue_type": "quantity_mismatch",
                    "description": f"Expected quantity ≈ {expected} (1 × {freq_per_day}/day × {duration_days} days) but prescription states {written}. Difference: {abs(expected - written)}.",
                    "severity": "high", "confidence": 90.0,
                })

    # ---- cross-medicine checks ----
    # 5. Duplicate active-ingredient detection (Requirement 12)
    ingredient_map = {}
    for idx, med in enumerate(medicines):
        ing = med.get("active_ingredient")
        if ing:
            ingredient_map.setdefault(ing, []).append(idx)
    for ing, idxs in ingredient_map.items():
        if len(idxs) > 1:
            names = ", ".join(medicines[i]["name"] for i in idxs)
            issues.append({
                "medicine_index": None, "issue_type": "duplicate_ingredient",
                "description": f"Possible duplicate ingredient '{ing}' found in: {names}. Please verify with a healthcare professional before dispensing.",
                "severity": "high", "confidence": 90.0,
            })

    # ---- completeness score (Requirement 15) ----
    total_checks = max(len(medicines), 1) * 5  # name, strength, freq, duration, no-issues
    passed = 0
    for idx, med in enumerate(medicines):
        passed += 1 if med.get("name") else 0
        passed += 1 if (med.get("dosage") or med.get("strength")) else 0
        passed += 1 if med.get("frequency") else 0
        passed += 1 if med.get("duration") else 0
        med_issue_count = sum(1 for i in issues if i["medicine_index"] == idx)
        passed += 1 if med_issue_count == 0 else 0
    completeness_score = round((passed / total_checks) * 100) if total_checks else 0

    overall_confidence = round(
        sum(m.get("confidence") or 0 for m in medicines) / len(medicines), 1
    ) if medicines else 0.0

    return issues, completeness_score, overall_confidence


# ------------------------------------------------------------------------
# Feature: Allergy-based medicine alert.
#
# Checks a newly-extracted medicine list against a patient's stored
# allergies (food, medicine, chemical/active-ingredient, other). Returns
# issues in the SAME shape as analyse_prescription() — {medicine_index, ...}
# — so callers can append them directly to that prescription's issues list
# before insertion. Like the rest of this module, this only ever FLAGS a
# possible conflict for human verification; it never decides a medicine is
# unsafe on its own.
# ------------------------------------------------------------------------
def check_allergy_conflicts(medicines, allergies):
    """
    medicines: list of medicine dicts (as returned by extract_structured_fields)
    allergies: iterable of rows/dicts with 'category' and 'substance' keys
    """
    issues = []
    for idx, med in enumerate(medicines):
        name = (med.get("name") or "").lower()
        ingredient = (med.get("active_ingredient") or "").lower()
        ingredient_parts = [p.strip() for p in ingredient.split("+")] if ingredient else []

        for allergy in allergies:
            substance = (allergy["substance"] or "").strip().lower()
            if not substance:
                continue

            matched_term = None
            if name and substance in name:
                matched_term = med.get("name")
            elif ingredient and substance in ingredient:
                matched_term = ingredient
            else:
                cross_ref = ALLERGY_CROSS_REFERENCE.get(substance)
                if cross_ref:
                    for part in ingredient_parts:
                        if part in cross_ref:
                            matched_term = part
                            break

            if matched_term:
                issues.append({
                    "medicine_index": idx,
                    "issue_type": "allergy_alert",
                    "description": (
                        f"{med.get('name') or 'This medicine'} contains or is related to "
                        f"'{matched_term}', which matches your recorded {allergy['category']} "
                        f"allergy to '{allergy['substance']}'. Do not take this medicine until "
                        f"a doctor or pharmacist has confirmed it is safe for you."
                    ),
                    "severity": "high",
                    "confidence": 80.0,
                })

    return issues


# ------------------------------------------------------------------------
# Feature: Disease/condition-based medicine alert.
#
# Checks a newly-extracted medicine list against a patient's stored health
# conditions (e.g. asthma, kidney disease, pregnancy) the same way
# check_allergy_conflicts() checks allergies. Returns issues in the SAME
# shape — {medicine_index, ...} — so callers can append them directly to
# that prescription's issues list before insertion. Like the rest of this
# module, this only ever FLAGS a possible conflict for human verification;
# it never tells a patient to stop or avoid a medicine on its own.
# ------------------------------------------------------------------------
def _canonical_condition(raw_condition):
    """Resolves free-text condition wording (e.g. 'chronic kidney disease',
    'high BP') to a canonical key in DISEASE_MEDICINE_CONFLICTS, using
    DISEASE_ALIASES. Matching is substring-based in both directions so
    minor phrasing differences still match. Returns None if nothing in the
    knowledge base corresponds to this condition — it is simply not
    checked, not treated as "no conflict possible"."""
    text = (raw_condition or "").strip().lower()
    if not text:
        return None
    if text in DISEASE_ALIASES:
        return DISEASE_ALIASES[text]
    # Longest alias first, so "chronic kidney disease" matches "kidney
    # disease" rather than a shorter, less specific alias by accident. Very
    # short aliases (e.g. "bp") require an exact match rather than a
    # substring match, to avoid false-positive matches inside unrelated words.
    for alias in sorted(DISEASE_ALIASES, key=len, reverse=True):
        if len(alias) < 4:
            continue
        if alias in text or text in alias:
            return DISEASE_ALIASES[alias]
    return None


def check_disease_conflicts(medicines, diseases):
    """
    medicines: list of medicine dicts (as returned by extract_structured_fields)
    diseases: iterable of rows/dicts with a 'condition_name' key
    """
    issues = []
    for idx, med in enumerate(medicines):
        ingredient = (med.get("active_ingredient") or "").lower()
        if not ingredient:
            continue
        ingredient_parts = [p.strip() for p in ingredient.split("+")]

        for disease in diseases:
            condition_key = _canonical_condition(disease["condition_name"])
            if not condition_key:
                continue
            conflicts = DISEASE_MEDICINE_CONFLICTS.get(condition_key, [])
            for conflict in conflicts:
                if conflict["ingredient"] not in ingredient_parts and conflict["ingredient"] != ingredient:
                    continue
                issues.append({
                    "medicine_index": idx,
                    "issue_type": "disease_conflict",
                    "description": (
                        f"{med.get('name') or 'This medicine'} contains {conflict['ingredient']}, "
                        f"which may worsen or interact badly with your recorded condition "
                        f"'{disease['condition_name']}'. {conflict['description']} "
                        f"Please confirm with a doctor or pharmacist before taking this medicine."
                    ),
                    "severity": conflict["severity"],
                    "confidence": 80.0,
                })

    return issues


# ------------------------------------------------------------------------
# Feature: Multiple-prescription drug interaction detection.
#
# Unlike the checks above, this operates ACROSS prescriptions — it takes a
# flat list of medicines the patient is currently on (potentially from
# several prescriptions written by different doctors, uploaded together or
# at different times) and looks for pairs whose active ingredients are
# known to interact. Each input record must already have real database ids
# (medicine_id, prescription_id) since results are written back as issues
# on the specific prescriptions/medicines involved, not a fresh batch.
# ------------------------------------------------------------------------
def find_drug_interactions(all_medicines):
    """
    all_medicines: list of dicts with keys: medicine_id, prescription_id,
                   name, active_ingredient
    Returns a list of dicts describing each interacting pair found:
      {medicine_id_a, prescription_id_a, name_a,
       medicine_id_b, prescription_id_b, name_b,
       severity, description}
    Each unordered pair of distinct medicines is checked once.
    """
    results = []
    n = len(all_medicines)
    for i in range(n):
        for j in range(i + 1, n):
            a, b = all_medicines[i], all_medicines[j]
            if a["medicine_id"] == b["medicine_id"]:
                continue

            ing_a = (a.get("active_ingredient") or "").lower()
            ing_b = (b.get("active_ingredient") or "").lower()
            if not ing_a or not ing_b:
                continue

            comps_a = [p.strip() for p in ing_a.split("+")]
            comps_b = [p.strip() for p in ing_b.split("+")]

            match = None
            for ca in comps_a:
                for cb in comps_b:
                    if ca == cb:
                        continue
                    info = DRUG_INTERACTIONS.get(frozenset({ca, cb}))
                    if info:
                        match = info
                        break
                if match:
                    break

            if match:
                results.append({
                    "medicine_id_a": a["medicine_id"], "prescription_id_a": a["prescription_id"], "name_a": a["name"],
                    "medicine_id_b": b["medicine_id"], "prescription_id_b": b["prescription_id"], "name_b": b["name"],
                    "severity": match["severity"], "description": match["description"],
                })

    return results


# ------------------------------------------------------------------------
# Feature: Look-alike/sound-alike (LASA) drug name confusion detection.
#
# Two complementary checks against knowledge_base.LASA_PAIRS:
#
#   1. STATIC AWARENESS FLAG — if a medicine on this prescription is one
#      half of a known LASA pair, always raise a (medium-severity) reminder
#      naming its confusable partner. This mirrors how real pharmacy
#      systems use "Tall Man lettering" warnings: they fire whenever the
#      drug is dispensed, not only when this specific instance of text
#      looks ambiguous, because the confusion risk lives in the
#      prescriber's/pharmacist's memory, not just in a given OCR pass.
#
#   2. FUZZY MISREAD FLAG — separately, scan raw-text word tokens against
#      ONLY the two members of each known pair (not the whole medicine
#      dictionary, which would produce noisy, unrelated near-matches). If a
#      single word is a close spelling match to BOTH members of a pair, an
#      actual OCR/handwriting misread is a real possibility — a stronger
#      (high-severity) signal than check 1 alone.
#
# STRICT RULE (same as the rest of this module): neither check changes
# which medicine was extracted or substitutes a "more likely" name — they
# only add issues for a human verifier to see.
# ------------------------------------------------------------------------
_LASA_WORD_PATTERN = re.compile(r"[a-zA-Z][a-zA-Z\-]{3,}")
_LASA_FUZZY_CUTOFF = 0.6


def check_lasa_confusion(raw_text, medicines):
    """
    raw_text: the original OCR/pasted text for one prescription
    medicines: list of medicine dicts already produced by
               extraction.extract_structured_fields() for the SAME text
    Returns issues in the same {medicine_index, issue_type, ...} shape as
    analyse_prescription(), so callers can append them directly.
    """
    issues = []
    name_to_idx = {
        med["name"].strip().lower(): idx
        for idx, med in enumerate(medicines) if med.get("name")
    }
    words = set(w.lower() for w in _LASA_WORD_PATTERN.findall(raw_text or ""))

    for pair, note in LASA_PAIRS.items():
        a, b = tuple(pair)
        a_present = a in name_to_idx or a in words
        b_present = b in name_to_idx or b in words

        if a_present and b_present:
            # Both names literally appear on this prescription — most
            # likely two separate, correctly-written medicines, not a
            # misread. Not this check's job to second-guess that.
            continue

        if a_present or b_present:
            present, other = (a, b) if a_present else (b, a)
            issues.append({
                "medicine_index": name_to_idx.get(present),
                "issue_type": "lasa_confusion_risk",
                "description": (
                    f"'{present.title()}' is on a known look-alike/sound-alike (LASA) list "
                    f"with '{other.title()}'. {note} Please double-check this is the medicine "
                    f"that was actually intended."
                ),
                "severity": "medium",
                "confidence": 70.0,
            })
            continue

        # Neither name appears exactly — check for a word that's fuzzily
        # close to BOTH pair members, suggesting an actual misread.
        for word in words:
            if len(word) < 4:
                continue
            ratio_a = difflib.SequenceMatcher(None, word, a).ratio()
            ratio_b = difflib.SequenceMatcher(None, word, b).ratio()
            if ratio_a >= _LASA_FUZZY_CUTOFF and ratio_b >= _LASA_FUZZY_CUTOFF:
                issues.append({
                    "medicine_index": None,
                    "issue_type": "lasa_confusion_risk",
                    "description": (
                        f"The text '{word}' is close enough in spelling to match both "
                        f"'{a.title()}' and '{b.title()}' — two different medicines that are "
                        f"commonly confused. {note} Please confirm the intended medicine "
                        f"directly with the prescriber before dispensing."
                    ),
                    "severity": "high",
                    "confidence": 55.0,
                })
                break

    return issues


# ------------------------------------------------------------------------
# Feature: Cumulative/multi-prescription dose-overload tracking.
#
# find_drug_interactions() (above) looks for DIFFERENT ingredients that
# interact badly. This function looks for the SAME ingredient arriving from
# more than one medicine — possibly under different brand names (Paracetamol
# + Dolo 650), possibly from different prescriptions written by different
# doctors on different days — and sums the total daily dose. A single
# prescription's duplicate-ingredient check (in analyse_prescription) cannot
# catch this, because the overdose only becomes visible once every ACTIVE
# prescription a patient holds is considered together.
#
# STRICT RULE (same as the rest of this module): this only ever flags a
# possible cumulative-dose concern for human verification. It never tells a
# patient to stop, skip, or adjust a dose on its own.
# ------------------------------------------------------------------------
_STRENGTH_PATTERN = re.compile(r"([\d.]+)\s*(mg|mcg|g|ml)\b", re.I)
_STRENGTH_UNIT_TO_MG = {"mg": 1, "g": 1000, "mcg": 0.001}


def _strength_to_mg(strength):
    """Parses a strength string like '500 mg' or '1 g' into a mg value.
    Returns None (rather than guessing) for units that don't convert
    cleanly to a dose weight, e.g. 'ml' (a volume, not a fixed mg amount
    without knowing concentration) or unparseable text."""
    if not strength:
        return None
    m = _STRENGTH_PATTERN.search(strength)
    if not m:
        return None
    value, unit = float(m.group(1)), m.group(2).lower()
    factor = _STRENGTH_UNIT_TO_MG.get(unit)
    if factor is None:
        return None
    return value * factor


def check_cumulative_dose(all_medicines):
    """
    all_medicines: list of dicts with keys: medicine_id, prescription_id,
                   name, active_ingredient, strength, frequency
                   (frequency should be the RAW token, e.g. 'bd', '1-0-1',
                   so it can be resolved back to a times-per-day count the
                   same way analyse_prescription() does)
    Returns a list of dicts, one per ingredient that crosses its safe daily
    ceiling:
      {ingredient, total_mg_per_day, max_mg_per_day, contributing:
        [ {medicine_id, prescription_id, name, mg_per_day}, ... ]}

    Medicines whose strength or frequency can't be confidently parsed into
    a numeric mg/day figure are skipped for THIS check (not treated as
    "zero dose") — they still go through every other check in this module.
    """
    per_ingredient = defaultdict(list)

    for med in all_medicines:
        ingredient_field = (med.get("active_ingredient") or "").lower()
        if not ingredient_field:
            continue
        mg = _strength_to_mg(med.get("strength"))
        freq_per_day = _frequency_to_per_day(med.get("frequency"))
        if mg is None or not freq_per_day:
            continue
        for component in ingredient_field.split("+"):
            component = component.strip()
            if component not in MAX_SAFE_DAILY_DOSE_MG:
                continue
            per_ingredient[component].append({
                "medicine_id": med["medicine_id"],
                "prescription_id": med["prescription_id"],
                "name": med["name"],
                "mg_per_day": mg * freq_per_day,
            })

    results = []
    for ingredient, contributions in per_ingredient.items():
        total = sum(c["mg_per_day"] for c in contributions)
        max_mg = MAX_SAFE_DAILY_DOSE_MG[ingredient]
        if total > max_mg:
            results.append({
                "ingredient": ingredient,
                "total_mg_per_day": round(total),
                "max_mg_per_day": max_mg,
                "contributing": contributions,
            })
    return results


# ------------------------------------------------------------------------
# Feature: Risk-priority verification queue.
#
# Turns a prescription's list of OPEN issues into a single sortable risk
# score, so the verifier dashboard can present the riskiest prescriptions
# first instead of plain upload-order (FIFO) — the same triage principle
# used in real clinical decision-support / pharmacy queues. The score
# rewards both severity and issue count, and weights each issue by the
# system's own confidence in it, so a barely-confident low-severity flag
# can't outrank a highly-confident high-severity one.
# ------------------------------------------------------------------------
def compute_risk_score(issues):
    """
    issues: iterable of dicts/rows with 'severity' ('high'/'medium'/'low')
            and 'confidence' (0-100 or None) keys — e.g. rows from the
            `issues` table, or the in-memory issue dicts used elsewhere in
            this module.
    Returns a single non-negative float; higher = more urgent to review.
    """
    score = 0.0
    for issue in issues:
        weight = SEVERITY_WEIGHT.get(issue.get("severity") if isinstance(issue, dict) else issue["severity"], 1)
        conf = issue.get("confidence") if isinstance(issue, dict) else issue["confidence"]
        confidence_factor = (conf if conf is not None else 50.0) / 100.0
        score += weight * confidence_factor
    return round(score, 2)
