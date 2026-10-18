"""
app.py — Prescription Safety & Ambiguity Detection System
Main Flask application: authentication, routing, and orchestration of the
upload -> extract -> analyse -> verify -> download workflow.

Run with:  python app.py   (after running: python db.py)
"""
import os
from collections import defaultdict
from functools import wraps
from flask import (Flask, render_template, request, redirect, url_for,
                    session, flash, send_from_directory, abort)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

import db
from extraction import run_ocr, extract_text_from_pdf, extract_structured_fields
from rules_engine import (analyse_prescription, confidence_band,
                           check_allergy_conflicts, check_disease_conflicts, find_drug_interactions,
                           check_lasa_confusion, check_cumulative_dose, compute_risk_score)
from pdf_generator import generate_prescription_pdf, generate_patient_report_pdf
from knowledge_base import (ABBREVIATIONS, ISSUE_TYPE_EXPLANATIONS, translate_phrase_to_tamil,
                             translate_medicine_name_to_tamil, translate_dosage_to_tamil)

def _start_keep_alive():
    """
    Pings this app's own /healthz endpoint every 10 minutes so Render's free
    tier doesn't spin the service down after 15 minutes of inactivity.

    Only runs when RENDER_EXTERNAL_URL is set (Render provides this env var
    automatically in production), so it stays inactive during local dev —
    'requests' is only imported once we've confirmed we're on Render, so it
    isn't a required dependency for running the app locally.
    """
    self_url = os.environ.get("RENDER_EXTERNAL_URL")
    if not self_url:
        return  # not running on Render (e.g. local dev) — skip

    import threading
    import time
    import requests

    def ping_loop():
        while True:
            time.sleep(600)  # 10 minutes — comfortably under the 15-min sleep threshold
            try:
                requests.get(f"{self_url}/healthz", timeout=10)
            except requests.RequestException:
                pass  # a missed ping isn't fatal, just try again next cycle

    thread = threading.Thread(target=ping_loop, daemon=True)
    thread.start()


ALLERGY_CATEGORIES = ("food", "medicine", "chemical", "other")

BASE_DIR = os.path.dirname(__file__)
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
GENERATED_DIR = os.path.join(BASE_DIR, "instance", "generated")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}
MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(GENERATED_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = "change-this-secret-key-in-production"
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH


@app.route("/healthz")
def healthz():
    """Lightweight endpoint for the keep-alive ping and Render's own health checks."""
    return "ok", 200


_start_keep_alive()


# ---------------------------------------------------------------- helpers --
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                flash("Please log in to continue.", "warning")
                return redirect(url_for("login"))
            if role and session.get("role") != role:
                flash("You don't have access to that page.", "danger")
                return redirect(url_for("home"))
            return f(*args, **kwargs)
        return wrapped
    return decorator


@app.context_processor
def inject_globals():
    return {"session": session, "lang": session.get("lang", "en")}


# ------------------------------------------------------------- public ----
@app.route("/debug-extraction")
def debug_extraction():
    import extraction, inspect
    src = inspect.getsource(extraction)
    has_new = "100.0 if strength" in src
    has_old = "85.0 if strength" in src
    return (
        "<pre style='font-size:14px;white-space:pre-wrap;'>"
        f"File Python is actually loading:\n{extraction.__file__}\n\n"
        f"Contains NEW formula (100.0 if strength...): {has_new}\n"
        f"Contains OLD formula (85.0 if strength...): {has_old}\n\n"
        "If 'old' is True, that exact file path above is the one you need to edit —\n"
        "there may be a second copy of extraction.py somewhere Python is finding first."
        "</pre>"
    )


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/how-it-works")
def how_it_works():
    return render_template("how_it_works.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/set-language/<lang>")
def set_language(lang):
    if lang in ("en", "ta"):
        session["lang"] = lang
    return redirect(request.referrer or url_for("home"))


# --------------------------------------------------------------- auth ----
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        confirm = request.form.get("confirm_password", "")
        role = request.form["role"]
        professional_id = request.form.get("professional_id", "").strip()

        if role == "patient" and password != confirm:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("register"))
        if role == "verifier" and not professional_id:
            flash("Professional ID is required for verifier accounts.", "danger")
            return redirect(url_for("register"))

        conn = db.get_db()
        existing = conn.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone()
        if existing:
            flash("An account with that email already exists.", "danger")
            conn.close()
            return redirect(url_for("register"))

        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash, role, professional_id) VALUES (?,?,?,?,?)",
            (name, email, generate_password_hash(password), role, professional_id or None),
        )
        new_user_id = cur.lastrowid

        # Allergy-based medicine alert (Feature): collect allergies at
        # registration for patient accounts. Rows arrive as parallel arrays
        # since the form lets the user add any number of allergy entries.
        if role == "patient":
            categories = request.form.getlist("allergy_category[]")
            substances = request.form.getlist("allergy_substance[]")
            notes_list = request.form.getlist("allergy_notes[]")
            for category, substance, notes in zip(categories, substances, notes_list):
                substance = substance.strip()
                if not substance:
                    continue
                if category not in ALLERGY_CATEGORIES:
                    category = "other"
                conn.execute(
                    "INSERT INTO allergies (user_id, category, substance, notes) VALUES (?,?,?,?)",
                    (new_user_id, category, substance, notes.strip() or None),
                )

            # Disease/condition-based medicine alert (Feature): collect known
            # health conditions at registration too, same parallel-array
            # pattern as allergies above.
            conditions = request.form.getlist("disease_condition[]")
            disease_notes_list = request.form.getlist("disease_notes[]")
            for condition, notes in zip(conditions, disease_notes_list):
                condition = condition.strip()
                if not condition:
                    continue
                conn.execute(
                    "INSERT INTO diseases (user_id, condition_name, notes) VALUES (?,?,?)",
                    (new_user_id, condition, notes.strip() or None),
                )

        conn.commit()
        conn.close()
        flash("Account created. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        conn = db.get_db()
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["user_id"]
            session["name"] = user["name"]
            session["role"] = user["role"]
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for("verifier_dashboard") if user["role"] == "verifier" else url_for("patient_dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ------------------------------------------------------- patient area ----
@app.route("/dashboard")
@login_required(role="patient")
def patient_dashboard():
    conn = db.get_db()
    rows = conn.execute(
        "SELECT * FROM prescriptions WHERE user_id=? ORDER BY upload_date DESC",
        (session["user_id"],),
    ).fetchall()

    # Per-prescription open-issue count, used both for the total "open
    # warnings" stat and for the "warnings" filter below.
    warning_counts = {}
    for r in rows:
        warning_counts[r["prescription_id"]] = conn.execute(
            "SELECT COUNT(*) c FROM issues WHERE prescription_id=? AND status='open'",
            (r["prescription_id"],),
        ).fetchone()["c"]
    conn.close()

    stats = {
        "total": len(rows),
        "verified": sum(1 for r in rows if r["status"] == "verified"),
        "pending": sum(1 for r in rows if r["status"] == "pending_verification"),
        "warnings": sum(warning_counts.values()),
    }

    # Feature: clickable stat cards. Each card links back here with a
    # ?filter= value; the table below only shows prescriptions matching it.
    # Unknown/missing filter values fall back to "all" rather than erroring.
    filter_value = request.args.get("filter", "all")
    if filter_value == "verified":
        prescriptions = [r for r in rows if r["status"] == "verified"]
    elif filter_value == "pending":
        prescriptions = [r for r in rows if r["status"] == "pending_verification"]
    elif filter_value == "warnings":
        prescriptions = [r for r in rows if warning_counts.get(r["prescription_id"], 0) > 0]
    else:
        filter_value = "all"
        prescriptions = rows

    return render_template(
        "patient_dashboard.html",
        prescriptions=prescriptions,
        stats=stats,
        active_filter=filter_value,
        warning_counts=warning_counts,
    )


@app.route("/allergies", methods=["GET", "POST"])
@login_required(role="patient")
def allergies():
    conn = db.get_db()
    if request.method == "POST":
        category = request.form.get("category", "other")
        substance = request.form.get("substance", "").strip()
        notes = request.form.get("notes", "").strip()
        if category not in ALLERGY_CATEGORIES:
            category = "other"
        if not substance:
            flash("Please enter the food, medicine, chemical, or substance you're allergic to.", "danger")
        else:
            conn.execute(
                "INSERT INTO allergies (user_id, category, substance, notes) VALUES (?,?,?,?)",
                (session["user_id"], category, substance, notes or None),
            )
            conn.commit()
            flash(f"Added allergy: {substance}.", "success")
        conn.close()
        return redirect(url_for("allergies"))

    rows = conn.execute(
        "SELECT * FROM allergies WHERE user_id=? ORDER BY created_at DESC", (session["user_id"],)
    ).fetchall()
    conn.close()
    return render_template("allergies.html", allergies=rows)


@app.route("/allergies/<int:allergy_id>/delete", methods=["POST"])
@login_required(role="patient")
def delete_allergy(allergy_id):
    conn = db.get_db()
    row = conn.execute("SELECT * FROM allergies WHERE allergy_id=?", (allergy_id,)).fetchone()
    if not row or row["user_id"] != session["user_id"]:
        conn.close()
        abort(403)
    conn.execute("DELETE FROM allergies WHERE allergy_id=?", (allergy_id,))
    conn.commit()
    conn.close()
    flash("Allergy removed.", "success")
    return redirect(url_for("allergies"))


@app.route("/diseases", methods=["GET", "POST"])
@login_required(role="patient")
def diseases():
    conn = db.get_db()
    if request.method == "POST":
        condition_name = request.form.get("condition_name", "").strip()
        notes = request.form.get("notes", "").strip()
        if not condition_name:
            flash("Please enter the health condition you'd like to record.", "danger")
        else:
            conn.execute(
                "INSERT INTO diseases (user_id, condition_name, notes) VALUES (?,?,?)",
                (session["user_id"], condition_name, notes or None),
            )
            conn.commit()
            flash(f"Added condition: {condition_name}.", "success")
        conn.close()
        return redirect(url_for("diseases"))

    rows = conn.execute(
        "SELECT * FROM diseases WHERE user_id=? ORDER BY created_at DESC", (session["user_id"],)
    ).fetchall()
    conn.close()
    return render_template("diseases.html", diseases=rows)


@app.route("/diseases/<int:disease_id>/delete", methods=["POST"])
@login_required(role="patient")
def delete_disease(disease_id):
    conn = db.get_db()
    row = conn.execute("SELECT * FROM diseases WHERE disease_id=?", (disease_id,)).fetchone()
    if not row or row["user_id"] != session["user_id"]:
        conn.close()
        abort(403)
    conn.execute("DELETE FROM diseases WHERE disease_id=?", (disease_id,))
    conn.commit()
    conn.close()
    flash("Condition removed.", "success")
    return redirect(url_for("diseases"))


def _process_one_prescription(conn, raw_text, image_path_rel, low_conf_words, allergies, patient_diseases):
    """
    Runs the extract -> analyse -> allergy-check -> disease-check -> insert
    pipeline for a SINGLE prescription (one file, or the pasted-text box)
    and returns its new prescription_id. Drug-interaction checking is
    deliberately NOT done here — it needs to see every medicine across every
    prescription the patient has, so it runs once, after all prescriptions
    in this request have been inserted (see upload()).
    """
    medicines = extract_structured_fields(raw_text, low_conf_words)
    issues, completeness_score, overall_confidence = analyse_prescription(medicines)
    issues += check_allergy_conflicts(medicines, allergies)
    issues += check_disease_conflicts(medicines, patient_diseases)
    # Feature: LASA (look-alike/sound-alike) name-confusion detection — scans
    # the raw text independently of which name extraction.py picked.
    issues += check_lasa_confusion(raw_text, medicines)

    cur = conn.execute(
        "INSERT INTO prescriptions (user_id, image_path, raw_text, overall_confidence, completeness_score) "
        "VALUES (?,?,?,?,?)",
        (session["user_id"], image_path_rel, raw_text, overall_confidence, completeness_score),
    )
    prescription_id = cur.lastrowid

    med_ids = []
    for med in medicines:
        mcur = conn.execute(
            "INSERT INTO medicines (prescription_id, name, active_ingredient, strength, dosage, "
            "frequency, frequency_expanded, duration, quantity, food_instruction, confidence) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (prescription_id, med["name"], med["active_ingredient"], med["strength"], med["dosage"],
             med["frequency"], med["frequency_expanded"], med["duration"], med["quantity"],
             med["food_instruction"], med["confidence"]),
        )
        med_ids.append(mcur.lastrowid)

    for issue in issues:
        med_id = med_ids[issue["medicine_index"]] if issue["medicine_index"] is not None else None
        conn.execute(
            "INSERT INTO issues (prescription_id, medicine_id, issue_type, description, severity, confidence) "
            "VALUES (?,?,?,?,?,?)",
            (prescription_id, med_id, issue["issue_type"], issue["description"], issue["severity"], issue["confidence"]),
        )

    return prescription_id


def _flag_interactions_for_user(conn, user_id):
    """
    Feature: Multiple-prescription drug interaction detection.

    Re-checks the patient's FULL active medicine list (across every
    prescription that hasn't been rejected — not just the ones just
    uploaded) so that interactions are caught even when the conflicting
    prescriptions were uploaded on different days by different doctors.

    Returns (new_alerts, interactions): the number of NEW interaction alerts
    written (so the caller can tell the patient how many were found), and the
    full list of interaction dicts found this pass (new or already-flagged)
    so the caller can show the reasoning inline without a second DB query.
    """
    all_meds = conn.execute(
        "SELECT m.medicine_id, m.prescription_id, m.name, m.active_ingredient "
        "FROM medicines m JOIN prescriptions p ON p.prescription_id = m.prescription_id "
        "WHERE p.user_id=? AND p.status != 'rejected'",
        (user_id,),
    ).fetchall()
    all_meds = [dict(m) for m in all_meds]

    interactions = find_drug_interactions(all_meds)
    new_alerts = 0
    for it in interactions:
        for presc_id, med_id, other_name in (
            (it["prescription_id_a"], it["medicine_id_a"], it["name_b"]),
            (it["prescription_id_b"], it["medicine_id_b"], it["name_a"]),
        ):
            # De-dupe: don't re-flag the same pair every time an unrelated
            # new prescription is uploaded and this recomputes from scratch.
            already = conn.execute(
                "SELECT 1 FROM issues WHERE medicine_id=? AND issue_type='drug_interaction' "
                "AND description LIKE ?",
                (med_id, f"%{other_name}%"),
            ).fetchone()
            if already:
                continue
            conn.execute(
                "INSERT INTO issues (prescription_id, medicine_id, issue_type, description, severity, confidence) "
                "VALUES (?,?,?,?,?,?)",
                (presc_id, med_id, "drug_interaction",
                 f"Possible interaction with {other_name} from another prescription: {it['description']} "
                 f"Please verify with a doctor or pharmacist before taking these together.",
                 it["severity"], 85.0),
            )
            new_alerts += 1
    return new_alerts, interactions


def _flag_cumulative_dose_for_user(conn, user_id):
    """
    Feature: Cumulative/multi-prescription dose-overload tracking.

    Re-checks the patient's FULL active medicine list (across every
    prescription that hasn't been rejected) for any active ingredient whose
    SUMMED daily dose — across possibly different brand names and different
    prescriptions/doctors — crosses a known safe ceiling. This is invisible
    to the single-prescription duplicate-ingredient check, which only looks
    within one prescription at a time.

    Returns the list of over-limit ingredient dicts found this pass (see
    rules_engine.check_cumulative_dose for the shape), after writing any
    NEW alerts to the issues table (de-duped the same way interaction
    alerts are, so re-running this on an unrelated new upload doesn't
    spam duplicate rows).
    """
    all_meds = conn.execute(
        "SELECT m.medicine_id, m.prescription_id, m.name, m.active_ingredient, "
        "m.strength, m.frequency "
        "FROM medicines m JOIN prescriptions p ON p.prescription_id = m.prescription_id "
        "WHERE p.user_id=? AND p.status != 'rejected'",
        (user_id,),
    ).fetchall()
    all_meds = [dict(m) for m in all_meds]

    overloads = check_cumulative_dose(all_meds)
    for overload in overloads:
        other_names = ", ".join(f"{c['name']} ({round(c['mg_per_day'])}mg/day)" for c in overload["contributing"])
        for contributor in overload["contributing"]:
            already = conn.execute(
                "SELECT 1 FROM issues WHERE medicine_id=? AND issue_type='cumulative_overdose_risk' "
                "AND description LIKE ?",
                (contributor["medicine_id"], f"%{overload['ingredient']}%{overload['total_mg_per_day']}%"),
            ).fetchone()
            if already:
                continue
            conn.execute(
                "INSERT INTO issues (prescription_id, medicine_id, issue_type, description, severity, confidence) "
                "VALUES (?,?,?,?,?,?)",
                (contributor["prescription_id"], contributor["medicine_id"], "cumulative_overdose_risk",
                 f"Combined across your active prescriptions, '{overload['ingredient']}' totals approximately "
                 f"{overload['total_mg_per_day']}mg/day (safe limit is around {overload['max_mg_per_day']}mg/day), "
                 f"contributed by: {other_names}. Please review your total intake with a doctor or pharmacist "
                 f"before continuing all of these together.",
                 "high", 75.0),
            )
    return overloads


@app.route("/upload", methods=["GET", "POST"])
@login_required(role="patient")
def upload():
    if request.method == "POST":
        pasted_text = request.form.get("pasted_text", "").strip()
        # Feature: Multiple Prescription upload — the form now sends a
        # "files" field that can hold more than one file (from different
        # doctors, uploaded together), instead of a single "file".
        files = [f for f in request.files.getlist("files") if f and f.filename]

        if not files and not pasted_text:
            flash("Please upload one or more prescription images/PDFs, or paste prescription text.", "danger")
            return redirect(url_for("upload"))

        conn = db.get_db()
        allergies = conn.execute(
            "SELECT * FROM allergies WHERE user_id=?", (session["user_id"],)
        ).fetchall()
        patient_diseases = conn.execute(
            "SELECT * FROM diseases WHERE user_id=?", (session["user_id"],)
        ).fetchall()

        created_ids = []
        skipped = []

        for file in files:
            if not allowed_file(file.filename):
                skipped.append(file.filename)
                continue
            filename = secure_filename(f"{session['user_id']}_{os.urandom(4).hex()}_{file.filename}")
            save_path = os.path.join(UPLOAD_DIR, filename)
            file.save(save_path)

            ext = filename.rsplit(".", 1)[1].lower()
            if ext == "pdf":
                raw_text = extract_text_from_pdf(save_path)
                low_conf_words = []
                if not raw_text.strip():
                    flash(f"Could not extract text from '{file.filename}' (it may be a scanned image). "
                          f"Try uploading it as a photo instead, or paste the text.", "warning")
            else:
                raw_text, avg_conf, low_conf_words = run_ocr(save_path)
                if avg_conf < 50:
                    flash(f"⚠️ Image quality for '{file.filename}' is low. Some information may not be readable.", "warning")

            prescription_id = _process_one_prescription(conn, raw_text, filename, low_conf_words, allergies, patient_diseases)
            created_ids.append(prescription_id)

        if pasted_text:
            prescription_id = _process_one_prescription(conn, pasted_text, None, [], allergies, patient_diseases)
            created_ids.append(prescription_id)

        conn.commit()

        # Cross-prescription drug interaction check, across every active
        # prescription the patient has — run once all new ones are saved.
        new_alerts, interactions = _flag_interactions_for_user(conn, session["user_id"])
        conn.commit()

        # Cross-prescription cumulative dose check — same idea as the
        # interaction check above, but for too much of the SAME ingredient
        # (possibly under different brand names) rather than two different
        # ingredients that interact.
        _flag_cumulative_dose_for_user(conn, session["user_id"])
        conn.commit()

        if skipped:
            flash(f"Skipped unsupported file(s): {', '.join(skipped)}. Please upload JPG, PNG, or PDF.", "warning")

        if not created_ids:
            conn.close()
            return redirect(url_for("upload"))

        if len(created_ids) == 1:
            conn.close()
            flash("Prescription uploaded and analysed.", "success")
            return redirect(url_for("prescription_detail", prescription_id=created_ids[0]))

        # Feature: for a multi-prescription upload, show the combined report
        # (medicines from every prescription just uploaded + any interaction
        # reasoning between them) right here instead of redirecting away —
        # the interaction is exactly what the patient wants to see first.
        report_prescriptions = []
        for pid in created_ids:
            presc = conn.execute("SELECT * FROM prescriptions WHERE prescription_id=?", (pid,)).fetchone()
            meds = [dict(m) for m in conn.execute("SELECT * FROM medicines WHERE prescription_id=?", (pid,)).fetchall()]
            issue_med_ids = {
                i["medicine_id"] for i in conn.execute(
                    "SELECT medicine_id FROM issues WHERE prescription_id=? AND medicine_id IS NOT NULL", (pid,)
                ).fetchall()
            }
            for m in meds:
                m["has_alert"] = m["medicine_id"] in issue_med_ids
            report_prescriptions.append({"presc": dict(presc), "medicines": meds})

        # Only show interactions involving the medicines from THIS batch
        # (not every historical pair the patient has ever had flagged).
        batch_med_ids = {mid for p in report_prescriptions for mid in [m["medicine_id"] for m in p["medicines"]]}
        relevant_interactions = [
            it for it in interactions
            if it["medicine_id_a"] in batch_med_ids or it["medicine_id_b"] in batch_med_ids
        ]
        conn.close()

        return render_template(
            "upload_report.html",
            prescriptions=report_prescriptions,
            interactions=relevant_interactions,
            interaction_explanation=ISSUE_TYPE_EXPLANATIONS.get("drug_interaction"),
        )

    return render_template("upload.html")


@app.route("/prescription/<int:prescription_id>")
@login_required()
def prescription_detail(prescription_id):
    conn = db.get_db()
    presc = conn.execute("SELECT * FROM prescriptions WHERE prescription_id=?", (prescription_id,)).fetchone()
    if not presc:
        conn.close()
        abort(404)
    # access control: owner patient, or any verifier
    if session["role"] == "patient" and presc["user_id"] != session["user_id"]:
        conn.close()
        abort(403)

    medicines = conn.execute("SELECT * FROM medicines WHERE prescription_id=?", (prescription_id,)).fetchall()
    issues = conn.execute("SELECT * FROM issues WHERE prescription_id=?", (prescription_id,)).fetchall()
    conn.close()

    presc = dict(presc)
    medicines = [dict(m) for m in medicines]

    # Feature: explainable "why was this flagged" reasoning. Every issue
    # gets, in addition to its specific description (what happened on THIS
    # prescription), a generic "explanation" of the rule/check that can ever
    # raise an issue of that type — so a flagged item never shows as just a
    # red badge with no way to see why it exists.
    issues = [dict(i) for i in issues]
    for i in issues:
        i["explanation"] = ISSUE_TYPE_EXPLANATIONS.get(i["issue_type"])

    # Which medicines have at least one open issue — used for the Alert
    # column in both the English and Tamil medicines table. A cross-medicine
    # issue like duplicate_ingredient has no single medicine_id and won't
    # mark a specific row here, but it still appears in the issues list below.
    issue_medicine_ids = {i["medicine_id"] for i in issues if i["medicine_id"] is not None}
    low_conf_name_ids = {
        i["medicine_id"] for i in issues
        if i["issue_type"] == "low_confidence_name" and i["medicine_id"] is not None
    }

    # Per-medicine issue list, so the Alert badge next to each medicine can
    # expand in-place to show exactly why it was flagged, rather than
    # sending the reader to hunt through the separate Detected Issues list.
    medicine_issues = {}
    for i in issues:
        if i["medicine_id"] is not None:
            medicine_issues.setdefault(i["medicine_id"], []).append(i)

    # Feature: click-to-expand breakdown for the COMPLETENESS score too
    # (mirrors the confidence breakdown below) — shows exactly which of the
    # 5 per-medicine checks passed/failed, so "100/100" or "60/100" is never
    # an unexplained number either.
    completeness_breakdown = []
    for m in medicines:
        med_issue_count = sum(1 for i in issues if i["medicine_id"] == m["medicine_id"])
        checks = [
            ("Medicine name identified", bool(m.get("name"))),
            ("Strength / dosage found", bool(m.get("dosage") or m.get("strength"))),
            ("Frequency found", bool(m.get("frequency"))),
            ("Duration found", bool(m.get("duration"))),
            ("No open issues on this medicine", med_issue_count == 0),
        ]
        completeness_breakdown.append({
            "name": m.get("verified_name") or m.get("name") or "Unrecognised medicine",
            "passed": sum(1 for _, ok in checks if ok),
            "total": len(checks),
            "checks": checks,
        })

    for m in medicines:
        m["abbrev_meaning"] = ABBREVIATIONS.get((m["frequency"] or "").lower())
        m["has_alert"] = m["medicine_id"] in issue_medicine_ids
        m["issues_why"] = medicine_issues.get(m["medicine_id"], [])

        # Feature: confidence breakdown. The overall % is an average of 4
        # sub-scores; show each one so the number is never unexplained.
        #
        # IMPORTANT: the badge percentage shown next to each medicine is
        # DERIVED from these same 4 sub-scores, right here, rather than
        # read from m["confidence"] (the value stored in the database at
        # upload time). If we displayed the stored value instead, it would
        # reflect whatever confidence formula was in effect back when that
        # particular prescription was uploaded — so an old record could
        # show a badge that no longer matches the (current) breakdown
        # explaining it, exactly the kind of "85% but every line below
        # says 100%" mismatch this replaced. Deriving both from the same
        # calculation, every time the page renders, makes that impossible.
        name_conf = 60.0 if m["medicine_id"] in low_conf_name_ids else 100.0
        strength_conf = 100.0 if m.get("strength") else 20.0
        freq_conf = 100.0 if m.get("frequency") else 15.0
        duration_conf = 100.0 if m.get("duration") else 15.0
        m["confidence"] = round((name_conf + strength_conf + freq_conf + duration_conf) / 4, 1)
        m["band"] = confidence_band(m["confidence"])
        m["confidence_breakdown"] = [
            {"label": "Medicine name recognition", "value": name_conf,
             "detail": "Matched confidently" if name_conf == 100.0
                       else "OCR was unsure of this name — verify against the original image"},
            {"label": "Strength / dosage detected", "value": strength_conf,
             "detail": f"Found: {m['strength']}" if m.get("strength") else "Not found in the text"},
            {"label": "Frequency detected", "value": freq_conf,
             "detail": f"Found: {m['frequency']}" if m.get("frequency") else "Not found in the text"},
            {"label": "Duration detected", "value": duration_conf,
             "detail": f"Found: {m['duration']}" if m.get("duration") else "Not found in the text"},
        ]

    # Same fix, one level up: the "Overall extraction confidence" card at
    # the top of the page is the average of the medicines' confidence
    # scores — derive it from the scores we just (re)computed above, not
    # from presc["overall_confidence"] (frozen into the DB at upload time),
    # so it can never show a different number than what's actually on this
    # page below it.
    if medicines:
        presc["overall_confidence"] = round(sum(m["confidence"] for m in medicines) / len(medicines), 1)

        # Feature: click-to-reveal Tamil translation, independent of the
        # site-wide EN/தமிழ் nav toggle. Always compute these so the "View
        # in Tamil" section on this page works no matter what language the
        # rest of the site is currently set to.
        m["name_ta"] = translate_medicine_name_to_tamil(m.get("verified_name") or m.get("name"))
        m["dosage_ta"] = translate_dosage_to_tamil(m.get("verified_dosage") or m.get("dosage"))
        if m.get("food_instruction"):
            m["food_instruction_ta"] = translate_phrase_to_tamil(m["food_instruction"].lower())
        if m.get("frequency_expanded"):
            base = m["frequency_expanded"].split(" (")[0]
            m["frequency_expanded_ta"] = translate_phrase_to_tamil(base)

    # Compact list for the top confidence card's inline breakdown — reuses
    # the per-medicine confidence + breakdown already computed above, just
    # in the shape the top-of-page card needs (no scrolling down required).
    confidence_summary = [
        {"name": m.get("verified_name") or m.get("name") or "Unrecognised medicine",
         "confidence": m["confidence"], "breakdown": m["confidence_breakdown"]}
        for m in medicines
    ]

    return render_template("prescription_detail.html", presc=presc, medicines=medicines, issues=issues,
                            completeness_breakdown=completeness_breakdown, confidence_summary=confidence_summary)


@app.route("/prescription/<int:prescription_id>/delete", methods=["POST"])
@login_required(role="patient")
def delete_prescription(prescription_id):
    conn = db.get_db()
    presc = conn.execute("SELECT * FROM prescriptions WHERE prescription_id=?", (prescription_id,)).fetchone()
    if not presc or presc["user_id"] != session["user_id"]:
        conn.close()
        abort(403)

    # Clean up the uploaded image file too, if there was one, so deleted
    # prescriptions don't leave orphaned files behind on disk.
    if presc["image_path"]:
        try:
            os.remove(os.path.join(UPLOAD_DIR, presc["image_path"]))
        except OSError:
            pass

    conn.execute("DELETE FROM verifications WHERE prescription_id=?", (prescription_id,))
    conn.execute("DELETE FROM issues WHERE prescription_id=?", (prescription_id,))
    conn.execute("DELETE FROM medicines WHERE prescription_id=?", (prescription_id,))
    conn.execute("DELETE FROM prescriptions WHERE prescription_id=?", (prescription_id,))
    conn.commit()
    conn.close()
    flash("Prescription deleted.", "success")
    return redirect(url_for("patient_dashboard"))


@app.route("/prescription/<int:prescription_id>/download")
@login_required()
def download_prescription(prescription_id):
    conn = db.get_db()
    presc = conn.execute("SELECT * FROM prescriptions WHERE prescription_id=?", (prescription_id,)).fetchone()
    if not presc or presc["status"] != "verified":
        conn.close()
        flash("This prescription is not yet verified, so a digital prescription cannot be downloaded.", "warning")
        return redirect(url_for("prescription_detail", prescription_id=prescription_id))
    if session["role"] == "patient" and presc["user_id"] != session["user_id"]:
        conn.close()
        abort(403)

    medicines = [dict(m) for m in conn.execute("SELECT * FROM medicines WHERE prescription_id=?", (prescription_id,)).fetchall()]
    patient = conn.execute("SELECT name FROM users WHERE user_id=?", (presc["user_id"],)).fetchone()
    verifier = conn.execute("SELECT name FROM users WHERE user_id=?", (presc["verifier_id"],)).fetchone() if presc["verifier_id"] else None
    conn.close()

    out_path = os.path.join(GENERATED_DIR, f"prescription_{prescription_id}.pdf")
    generate_prescription_pdf(dict(presc), medicines, patient["name"], verifier["name"] if verifier else "N/A", out_path)
    return send_from_directory(GENERATED_DIR, os.path.basename(out_path), as_attachment=True)


@app.route("/my-health-record/download")
@login_required(role="patient")
def download_health_record():
    """
    Feature: PDF of all of a patient's data — a single, attractively laid
    out "health record" export covering their profile, recorded allergies
    and health conditions, and every prescription they've uploaded (verified
    or not) with its medicines and flagged issues. Unlike the per-
    prescription "Digital Prescription" PDF (download_prescription, above),
    this is generated on demand from whatever is in the database right now
    and is NOT gated on verification — it's the patient's own data, for
    their own records or to share with a new doctor.
    """
    user_id = session["user_id"]
    conn = db.get_db()
    patient = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    allergy_rows = conn.execute(
        "SELECT * FROM allergies WHERE user_id=? ORDER BY created_at", (user_id,)
    ).fetchall()
    disease_rows = conn.execute(
        "SELECT * FROM diseases WHERE user_id=? ORDER BY created_at", (user_id,)
    ).fetchall()
    presc_rows = conn.execute(
        "SELECT * FROM prescriptions WHERE user_id=? ORDER BY upload_date", (user_id,)
    ).fetchall()

    prescriptions_data = []
    for presc in presc_rows:
        pid = presc["prescription_id"]
        meds = [dict(m) for m in conn.execute(
            "SELECT * FROM medicines WHERE prescription_id=?", (pid,)
        ).fetchall()]
        issue_rows = [dict(i) for i in conn.execute(
            "SELECT * FROM issues WHERE prescription_id=?", (pid,)
        ).fetchall()]
        prescriptions_data.append({"presc": dict(presc), "medicines": meds, "issues": issue_rows})
    conn.close()

    out_path = os.path.join(GENERATED_DIR, f"health_record_{user_id}.pdf")
    generate_patient_report_pdf(
        dict(patient), [dict(a) for a in allergy_rows], [dict(d) for d in disease_rows],
        prescriptions_data, out_path,
    )
    return send_from_directory(GENERATED_DIR, os.path.basename(out_path), as_attachment=True,
                                download_name=f"RxVerify_Health_Record_{patient['name'].replace(' ', '_')}.pdf")


@app.route("/uploads/<path:filename>")
@login_required()
def uploaded_file(filename):
    # Only the owning patient or a verifier may view the raw prescription image.
    conn = db.get_db()
    presc = conn.execute("SELECT * FROM prescriptions WHERE image_path=?", (filename,)).fetchone()
    conn.close()
    if not presc:
        abort(404)
    if session["role"] == "patient" and presc["user_id"] != session["user_id"]:
        abort(403)
    return send_from_directory(UPLOAD_DIR, filename)


# ------------------------------------------------------ verifier area ----
@app.route("/verifier/dashboard")
@login_required(role="verifier")
def verifier_dashboard():
    """
    Feature: Risk-priority verification queue.

    Rather than a plain FIFO (oldest-upload-first) queue, prescriptions are
    ranked by a computed risk score — combining issue severity, issue count,
    and the system's own confidence in each flag — so the riskiest
    prescriptions surface first. This mirrors triage in real clinical
    verification workflows. Ties (including prescriptions with no open
    issues) fall back to upload order, so nothing is silently starved at
    the bottom of the queue forever.
    """
    conn = db.get_db()
    rows = conn.execute(
        "SELECT p.*, u.name as patient_name "
        "FROM prescriptions p JOIN users u ON u.user_id = p.user_id "
        "WHERE p.status='pending_verification'"
    ).fetchall()
    rows = [dict(r) for r in rows]

    issues_by_presc = defaultdict(list)
    if rows:
        placeholders = ",".join("?" * len(rows))
        issue_rows = conn.execute(
            f"SELECT prescription_id, severity, confidence FROM issues "
            f"WHERE status='open' AND prescription_id IN ({placeholders})",
            tuple(r["prescription_id"] for r in rows),
        ).fetchall()
        for i in issue_rows:
            issues_by_presc[i["prescription_id"]].append(dict(i))
    conn.close()

    for r in rows:
        presc_issues = issues_by_presc.get(r["prescription_id"], [])
        r["issue_count"] = len(presc_issues)
        r["risk_score"] = compute_risk_score(presc_issues)
        r["top_severity"] = next(
            (s for s in ("high", "medium", "low") if any(i["severity"] == s for i in presc_issues)),
            None,
        )

    # Highest risk first; tie-break by oldest upload so nothing waits forever.
    rows.sort(key=lambda r: (-r["risk_score"], r["upload_date"]))

    return render_template("verifier_dashboard.html", prescriptions=rows)


@app.route("/verifier/prescription/<int:prescription_id>", methods=["GET", "POST"])
@login_required(role="verifier")
def verify_prescription(prescription_id):
    conn = db.get_db()
    presc = conn.execute("SELECT * FROM prescriptions WHERE prescription_id=?", (prescription_id,)).fetchone()
    if not presc:
        conn.close()
        abort(404)
    medicines = conn.execute("SELECT * FROM medicines WHERE prescription_id=?", (prescription_id,)).fetchall()

    if request.method == "POST":
        for med in medicines:
            mid = med["medicine_id"]
            for field in ("name", "dosage", "frequency", "duration", "quantity"):
                new_val = request.form.get(f"verified_{field}_{mid}", "").strip()
                old_val = med[field]
                if new_val:
                    conn.execute(f"UPDATE medicines SET verified_{field}=? WHERE medicine_id=?", (new_val, mid))
                    status = "confirmed" if new_val == (old_val or "") else "corrected"
                    conn.execute(
                        "INSERT INTO verifications (prescription_id, medicine_id, verifier_id, field_name, "
                        "original_value, corrected_value, verification_status) VALUES (?,?,?,?,?,?,?)",
                        (prescription_id, mid, session["user_id"], field, old_val, new_val, status),
                    )
        conn.execute(
            "UPDATE prescriptions SET status='verified', verifier_id=?, verified_at=CURRENT_TIMESTAMP WHERE prescription_id=?",
            (session["user_id"], prescription_id),
        )
        conn.execute("UPDATE issues SET status='resolved' WHERE prescription_id=?", (prescription_id,))
        conn.commit()
        conn.close()
        flash("Prescription marked as verified.", "success")
        return redirect(url_for("verifier_dashboard"))

    issues = conn.execute("SELECT * FROM issues WHERE prescription_id=?", (prescription_id,)).fetchall()
    conn.close()
    medicines = [dict(m) for m in medicines]
    for m in medicines:
        m["band"] = confidence_band(m["confidence"])
    issues = [dict(i) for i in issues]
    for i in issues:
        i["explanation"] = ISSUE_TYPE_EXPLANATIONS.get(i["issue_type"])
    return render_template("verify_prescription.html", presc=presc, medicines=medicines, issues=issues)


if __name__ == "__main__":
    # init_db() only ever runs CREATE TABLE IF NOT EXISTS statements, so it's
    # safe to call unconditionally — this is what lets a brand-new table
    # (like "allergies") get added to a database that was created before
    # that table existed, without touching any existing data.hehe.
    db.init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)