"""
pdf_generator.py - builds PDF exports.

generate_prescription_pdf(): the final "Digital Prescription" PDF
(Requirement 21). Only ever called AFTER human verification, and only ever
uses verified values (falling back to the AI-extracted value if a verifier
explicitly confirmed it).

generate_patient_report_pdf(): the full patient "Health Record" export
(Feature) - every recorded allergy/condition and every uploaded
prescription's medicines and flagged issues, styled as a single readable
document a patient could hand to a new doctor.
"""
from fpdf import FPDF
from datetime import datetime

# Brand palette, shared by both PDFs below.
NAVY = (26, 43, 66)
ACCENT = (37, 99, 172)
PAPER = (247, 249, 252)
LINE = (223, 229, 238)
RED = (192, 57, 43)
RED_BG = (253, 235, 233)
AMBER = (176, 111, 21)
AMBER_BG = (253, 244, 224)
GREEN = (39, 122, 78)
GREEN_BG = (231, 246, 238)
INK = (34, 40, 49)
INK_SOFT = (100, 112, 128)

SEVERITY_COLORS = {"high": (RED, RED_BG), "medium": (AMBER, AMBER_BG), "low": (GREEN, GREEN_BG)}

# fpdf2's built-in core fonts (Helvetica etc.) only support a limited
# character set and raise if asked to render anything outside it. Issue
# descriptions and free-text notes come from the database/live rule engine
# and can contain characters like "→" or "≈" that read fine in the web UI's
# Unicode-safe HTML but would crash PDF generation — so every piece of
# dynamic text is passed through this before being handed to a cell()/
# multi_cell() call, rather than trying to keep every upstream string
# PDF-safe by convention.
_PDF_CHAR_MAP = {
    "\u2192": "->", "\u2190": "<-", "\u2248": "~", "\u00d7": "x",
    "\u2013": "-", "\u2014": "-", "\u2026": "...", "\u00b7": "|",
    "\u2713": "[OK]", "\u2717": "[X]", "\u26a0": "[!]", "\ufe0f": "",
    "\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"',
}


def _pdf_safe(text):
    if text is None:
        return ""
    text = str(text)
    for bad, good in _PDF_CHAR_MAP.items():
        text = text.replace(bad, good)
    # Anything still outside Latin-1 after the map above (e.g. stray
    # emoji) is dropped rather than left to crash the whole PDF.
    return text.encode("latin-1", "ignore").decode("latin-1")


class HealthRecordPDF(FPDF):
    """FPDF subclass with a consistent branded header/footer on every page,
    used only by generate_patient_report_pdf() - the per-prescription
    "Digital Prescription" PDF keeps its own simpler, unbranded layout."""

    patient_name = ""
    generated_on = ""

    def header(self):
        self.set_fill_color(*NAVY)
        self.rect(0, 0, self.w, 20, "F")
        self.set_xy(12, 6)
        self.set_font("Helvetica", "B", 15)
        self.set_text_color(255, 255, 255)
        self.cell(0, 8, "RxVerify - Patient Health Record", ln=0)
        self.set_xy(-70, 6)
        self.set_font("Helvetica", "", 9)
        self.cell(58, 8, self.generated_on, align="R")
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_draw_color(*LINE)
        self.line(12, self.get_y(), self.w - 12, self.get_y())
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*INK_SOFT)
        self.set_y(-12)
        self.cell(0, 8, _pdf_safe(f"{self.patient_name} | AI-assisted export, not a medical document - verify with a doctor or pharmacist"), align="L")
        self.cell(0, 8, f"Page {self.page_no()}", align="R")

    def section_title(self, text):
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*NAVY)
        self.cell(0, 10, _pdf_safe(text), ln=True)
        self.set_draw_color(*ACCENT)
        self.set_line_width(0.6)
        y = self.get_y()
        self.line(12, y, 12 + 26, y)
        self.set_line_width(0.2)
        self.ln(4)

    def severity_chip(self, severity):
        color, bg = SEVERITY_COLORS.get(severity, (INK_SOFT, PAPER))
        label = severity.upper()
        self.set_font("Helvetica", "B", 8)
        w = self.get_string_width(label) + 6
        x, y = self.get_x(), self.get_y()
        self.set_fill_color(*bg)
        self.set_text_color(*color)
        self.cell(w, 6, label, fill=True, align="C")
        self.set_xy(x + w + 3, y)
        self.set_text_color(*INK)


def generate_prescription_pdf(prescription, medicines, patient_name, verifier_name, output_path):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "DIGITAL PRESCRIPTION", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, "AI-assisted verification tool - not a substitute for professional medical advice", ln=True, align="C")
    pdf.ln(6)

    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, f"Patient: {_pdf_safe(patient_name)}", ln=True)
    pdf.cell(0, 7, f"Prescription ID: P{prescription['prescription_id']:04d}", ln=True)
    pdf.cell(0, 7, f"Date: {prescription['upload_date']}", ln=True)
    pdf.ln(4)

    for i, med in enumerate(medicines, start=1):
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, f"Medicine {i}", ln=True)
        pdf.set_font("Helvetica", "", 11)
        rows = [
            ("Name", med["verified_name"] or med["name"] or "-"),
            ("Strength", med["strength"] or "-"),
            ("Dose", med["verified_dosage"] or med["dosage"] or "-"),
            ("Frequency", med["verified_frequency"] or med["frequency_expanded"] or med["frequency"] or "-"),
            ("Duration", med["verified_duration"] or med["duration"] or "-"),
            ("Quantity", med["verified_quantity"] or med["quantity"] or "-"),
            ("Food instruction", med["food_instruction"] or "-"),
        ]
        for label, value in rows:
            pdf.cell(45, 7, f"  {label}:", border=0)
            pdf.cell(0, 7, _pdf_safe(value), ln=True)
        pdf.ln(3)

    pdf.set_font("Helvetica", "I", 10)
    pdf.multi_cell(0, 6,
        "Verification: This prescription's key fields were reviewed and confirmed "
        f"by verifier: {_pdf_safe(verifier_name)} on {prescription.get('verified_at') or datetime.now().strftime('%Y-%m-%d %H:%M')}.\n\n"
        "This system does not diagnose diseases, prescribe medication, or change dosage. "
        "It assists in reading and cross-checking an existing prescription. Always follow "
        "the advice of a qualified doctor or pharmacist."
    )

    pdf.output(output_path)
    return output_path


def generate_patient_report_pdf(patient, allergy_rows, disease_rows, prescriptions_data, output_path):
    """
    patient: dict with at least 'name'
    allergy_rows: list of dicts (category, substance, notes)
    disease_rows: list of dicts (condition_name, notes)
    prescriptions_data: list of {'presc': dict, 'medicines': list[dict], 'issues': list[dict]},
                        oldest first - every prescription the patient has, any status.
    """
    pdf = HealthRecordPDF()
    pdf.patient_name = patient.get("name", "Patient")
    pdf.generated_on = f"Generated {datetime.now().strftime('%d %b %Y, %H:%M')}"
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # ---- Patient summary strip -------------------------------------------------
    pdf.set_fill_color(*PAPER)
    pdf.rect(12, pdf.get_y(), pdf.w - 24, 22, "F")
    pdf.set_xy(16, pdf.get_y() + 4)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*INK)
    pdf.cell(0, 8, _pdf_safe(patient.get("name", "Patient")), ln=True)
    pdf.set_x(16)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*INK_SOFT)
    total = len(prescriptions_data)
    verified = sum(1 for p in prescriptions_data if p["presc"]["status"] == "verified")
    open_issues = sum(1 for p in prescriptions_data for i in p["issues"] if i["status"] == "open")
    pdf.cell(0, 7, f"{total} prescription(s) on record  |  {verified} verified  |  {open_issues} open issue(s) flagged", ln=True)
    pdf.ln(10)

    # ---- Allergies ---------------------------------------------------------
    pdf.section_title("Recorded Allergies")
    if allergy_rows:
        for a in allergy_rows:
            pdf.set_font("Helvetica", "B", 10.5)
            pdf.set_text_color(*INK)
            pdf.cell(0, 6, _pdf_safe(f"- {a['substance']}  ({a['category']})"), ln=True)
            if a.get("notes"):
                pdf.set_font("Helvetica", "I", 9.5)
                pdf.set_text_color(*INK_SOFT)
                pdf.cell(0, 5, _pdf_safe(f"   {a['notes']}"), ln=True)
    else:
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(*INK_SOFT)
        pdf.cell(0, 6, "No allergies recorded.", ln=True)
    pdf.ln(4)

    # ---- Health conditions ---------------------------------------------------
    pdf.section_title("Recorded Health Conditions")
    if disease_rows:
        for d in disease_rows:
            pdf.set_font("Helvetica", "B", 10.5)
            pdf.set_text_color(*INK)
            pdf.cell(0, 6, _pdf_safe(f"- {d['condition_name']}"), ln=True)
            if d.get("notes"):
                pdf.set_font("Helvetica", "I", 9.5)
                pdf.set_text_color(*INK_SOFT)
                pdf.cell(0, 5, _pdf_safe(f"   {d['notes']}"), ln=True)
    else:
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(*INK_SOFT)
        pdf.cell(0, 6, "No health conditions recorded.", ln=True)
    pdf.ln(6)

    # ---- Prescriptions -------------------------------------------------------
    pdf.section_title(f"Prescription History ({len(prescriptions_data)})")
    if not prescriptions_data:
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(*INK_SOFT)
        pdf.cell(0, 6, "No prescriptions uploaded yet.", ln=True)

    for entry in prescriptions_data:
        presc, meds, issues = entry["presc"], entry["medicines"], entry["issues"]
        open_issues_here = [i for i in issues if i["status"] == "open"]

        # Card background sized to roughly fit the header + medicine rows;
        # auto page-break still applies for very long prescriptions.
        pdf.set_draw_color(*LINE)
        pdf.set_line_width(0.3)
        card_top = pdf.get_y()

        pdf.set_font("Helvetica", "B", 11.5)
        pdf.set_text_color(*NAVY)
        pdf.cell(0, 7, f"Prescription P{presc['prescription_id']:04d}  -  {presc['upload_date']}", ln=True)

        pdf.set_font("Helvetica", "", 9.5)
        status_color = GREEN if presc["status"] == "verified" else AMBER
        pdf.set_text_color(*INK_SOFT)
        status_label = "Verified" if presc["status"] == "verified" else "Verification required"
        pdf.cell(0, 6,
                 f"Status: {status_label}   |   Completeness: {presc['completeness_score']}/100   "
                 f"|   Extraction confidence: {presc['overall_confidence']}%",
                 ln=True)
        pdf.ln(1)

        if meds:
            col_w = [58, 30, 34, 34]
            headers = ["Medicine", "Dose", "Frequency", "Duration"]
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_fill_color(*NAVY)
            pdf.set_text_color(255, 255, 255)
            for w, h in zip(col_w, headers):
                pdf.cell(w, 7, h, fill=True, border=0)
            pdf.ln(7)

            pdf.set_font("Helvetica", "", 9)
            for i, m in enumerate(meds):
                pdf.set_fill_color(*PAPER if i % 2 == 0 else (255, 255, 255))
                pdf.set_text_color(*INK)
                row = [
                    _pdf_safe((m.get("verified_name") or m.get("name") or "Unrecognised")[:34]),
                    _pdf_safe((m.get("verified_dosage") or m.get("dosage") or "-")[:18]),
                    _pdf_safe((m.get("verified_frequency") or m.get("frequency_expanded") or m.get("frequency") or "-")[:20]),
                    _pdf_safe((m.get("verified_duration") or m.get("duration") or "-")[:20]),
                ]
                for w, val in zip(col_w, row):
                    pdf.cell(w, 6.5, val, fill=True, border=0)
                pdf.ln(6.5)
            pdf.ln(2)
        else:
            pdf.set_font("Helvetica", "I", 9.5)
            pdf.set_text_color(*INK_SOFT)
            pdf.cell(0, 6, "No medicines were extracted from this prescription.", ln=True)

        if open_issues_here:
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*RED)
            pdf.cell(0, 7, f"Flagged issues ({len(open_issues_here)})", ln=True)
            for issue in open_issues_here:
                pdf.set_x(16)
                pdf.severity_chip(issue["severity"])
                pdf.set_font("Helvetica", "", 9)
                pdf.set_text_color(*INK)
                remaining_w = pdf.w - pdf.get_x() - 12
                pdf.multi_cell(remaining_w, 5.5, _pdf_safe(issue["description"]))
                pdf.ln(0.5)
        else:
            pdf.set_font("Helvetica", "", 9.5)
            pdf.set_text_color(*GREEN)
            pdf.cell(0, 6, "No open issues on this prescription.", ln=True)

        card_bottom = pdf.get_y()
        pdf.set_draw_color(*LINE)
        pdf.line(12, card_bottom + 3, pdf.w - 12, card_bottom + 3)
        pdf.ln(7)

    # ---- Closing disclaimer -------------------------------------------------
    pdf.set_font("Helvetica", "I", 8.5)
    pdf.set_text_color(*INK_SOFT)
    pdf.multi_cell(0, 5,
        "This export reflects data currently stored in RxVerify at the time of download. It does not "
        "diagnose diseases, prescribe medication, or change dosage, and flagged issues are AI-generated "
        "prompts for human verification, not confirmed medical findings. Always confirm this record's "
        "contents, and any flagged issue, with a qualified doctor or pharmacist."
    )

    pdf.output(output_path)
    return output_path
