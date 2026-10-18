# RxVerify — Prescription Safety & Ambiguity Detection System

A college prototype that implements the "Essential" feature set:
upload → OCR/extract → confidence-score → flag ambiguity/missing/duplicate/
quantity issues → human (pharmacist) verification → verified digital
prescription PDF → history. Built with Flask + SQLite so it runs anywhere
with just Python.

**The system never edits or invents prescription content — it only flags
uncertainty and routes it to a human verifier.**

---

## 1. File map (what each file does)

```
prescription_safety_system/
│
├── requirements.txt        Python packages to install
├── schema.sql               Database table definitions
├── db.py                    Creates/opens the SQLite database
├── knowledge_base.py        Medicine→ingredient dictionary, abbreviation
│                            dictionary, English→Tamil phrase table
├── extraction.py            OCR (pytesseract) + rule-based NLP field
│                            extraction (Stages 1-3 of the AI pipeline)
├── rules_engine.py          Ambiguity / missing-field / duplicate-ingredient /
│                            quantity-consistency checks + completeness score
│                            (Stages 4-5 of the AI pipeline)
├── pdf_generator.py         Builds the final verified "Digital Prescription" PDF
├── app.py                   Flask app: routes, auth, and the upload→verify
│                            workflow that wires everything above together
│
├── templates/               HTML pages (Jinja2)
│   ├── base.html             Shared layout, nav, language toggle
│   ├── index.html             Landing page
│   ├── how_it_works.html      Pipeline explanation
│   ├── about.html             Project/safety statement
│   ├── register.html          Sign-up (role-aware fields)
│   ├── login.html
│   ├── patient_dashboard.html Stats + prescription history
│   ├── upload.html            Upload/paste form
│   ├── prescription_detail.html  Extraction, confidence, issues, explanation
│   ├── verifier_dashboard.html   Pharmacist queue
│   └── verify_prescription.html  Side-by-side human verification screen
│
├── static/style.css         All styling (single stylesheet)
├── uploads/                  Uploaded prescription images/PDFs (runtime)
└── instance/                 SQLite DB + generated PDFs (runtime, gitignore this)
```

## 2. Order to read the code in (for your report / viva)

1. `schema.sql` — understand the data model first
2. `db.py` — how the app talks to the database
3. `knowledge_base.py` — the reference dictionaries the intelligence relies on
4. `extraction.py` — how raw text/OCR turns into structured fields
5. `rules_engine.py` — the actual "ambiguity/error detection" logic (your core innovation)
6. `pdf_generator.py` — how a verified record becomes a document
7. `app.py` — how it's all wired into routes/pages
8. `templates/*.html` — the UI, in the order a user would click through them:
   `index → register/login → upload → prescription_detail → (verifier) verifier_dashboard → verify_prescription → back to prescription_detail (now downloadable)`

## 3. How to run it

```bash
cd prescription_safety_system
pip install -r requirements.txt

# System dependency (OCR engine) — install once per machine:
#   Ubuntu/Debian: sudo apt-get install tesseract-ocr
#   macOS:         brew install tesseract
#   Windows:       install tesseract-ocr and add it to PATH

python db.py        # creates instance/prescriptions.db
python app.py        # starts the server
```

Then open **http://localhost:5000**.

## 4. Demo script (suggested order for your presentation)

1. Register a **Patient** account, then register a **Verifier** account (use two browser tabs/profiles, or log out/in between).
2. As the patient: go to **Upload**, and use the "paste prescription text" box (most reliable for a live demo) with something like:
   ```
   Tab. Paracetamol 500mg 1-0-1 x 5 days #10
   Tab. Dolo 650 BD PC x 5 days
   Cap. Amoxicillin BD
   ```
   This deliberately demonstrates: a duplicate ingredient (Paracetamol/Dolo 650), an abbreviation (BD), and a missing duration (Amoxicillin).
3. Show the **Prescription Detail** page: confidence badges, completeness score, and the flagged issues.
4. Log in as the **Verifier**, open the **Verification Queue**, click into the prescription, and show the **side-by-side** original vs. AI extraction. Correct/confirm fields, then submit.
5. Log back in as the patient and **download the verified PDF**.
6. Toggle **English/Tamil** on the detail page to show the plain-language explanation feature.

To demo real OCR (not just pasted text), upload a clear, printed/typed prescription image — handwriting recognition will genuinely (and correctly) trigger lower confidence scores, which is the point of the project.

## 5. What was intentionally left out of this MVP

Per the project scope, the **Admin role** and a few "nice-to-have" items
(SMS/push notifications, live text-to-speech, professional-ID verification
against a real registry) were left out to keep the prototype focused and
defensible. The README/how-it-works page and code comments explain why —
useful talking points if your evaluator asks "why isn't X built?".
