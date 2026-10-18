-- Prescription Safety & Ambiguity Detection System
-- Database schema (SQLite)

CREATE TABLE IF NOT EXISTS users (
    user_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT NOT NULL,
    email          TEXT UNIQUE NOT NULL,
    password_hash  TEXT NOT NULL,
    role           TEXT NOT NULL CHECK(role IN ('patient', 'verifier')),
    professional_id TEXT,
    created_at     TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prescriptions (
    prescription_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id           INTEGER NOT NULL,
    image_path        TEXT,
    raw_text          TEXT,
    upload_date       TEXT DEFAULT CURRENT_TIMESTAMP,
    status            TEXT NOT NULL DEFAULT 'pending_verification'
                        CHECK(status IN ('pending_verification','verified','rejected')),
    overall_confidence REAL,
    completeness_score  INTEGER,
    verifier_id       INTEGER,
    verified_at       TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (verifier_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS medicines (
    medicine_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    prescription_id INTEGER NOT NULL,
    name            TEXT,
    active_ingredient TEXT,
    strength        TEXT,
    dosage          TEXT,
    frequency       TEXT,
    frequency_expanded TEXT,
    duration        TEXT,
    quantity        TEXT,
    food_instruction TEXT,
    confidence      REAL,
    verified_name       TEXT,
    verified_dosage     TEXT,
    verified_frequency  TEXT,
    verified_duration   TEXT,
    verified_quantity   TEXT,
    FOREIGN KEY (prescription_id) REFERENCES prescriptions(prescription_id)
);

CREATE TABLE IF NOT EXISTS issues (
    issue_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    prescription_id INTEGER NOT NULL,
    medicine_id     INTEGER,
    issue_type      TEXT NOT NULL,
    description     TEXT NOT NULL,
    severity        TEXT NOT NULL CHECK(severity IN ('high','medium','low')),
    confidence      REAL,
    status          TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','resolved')),
    FOREIGN KEY (prescription_id) REFERENCES prescriptions(prescription_id),
    FOREIGN KEY (medicine_id) REFERENCES medicines(medicine_id)
);

-- Patient-reported allergies, collected at registration and editable later
-- from the "My Allergies" page. Used by the allergy-alert checker in
-- rules_engine.py to flag medicines against a patient's known allergies.
CREATE TABLE IF NOT EXISTS allergies (
    allergy_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL,
    category       TEXT NOT NULL CHECK(category IN ('food','medicine','chemical','other')),
    substance      TEXT NOT NULL,
    notes          TEXT,
    created_at     TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Patient-reported medical conditions/diseases, collected at registration and
-- editable later from the "My Health Conditions" page. Used by the
-- disease-conflict checker in rules_engine.py to flag medicines that are
-- known to worsen or interact badly with a patient's recorded condition
-- (e.g. NSAIDs flagged for a patient with kidney disease).
CREATE TABLE IF NOT EXISTS diseases (
    disease_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL,
    condition_name TEXT NOT NULL,
    notes          TEXT,
    created_at     TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS verifications (
    verification_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    prescription_id    INTEGER NOT NULL,
    medicine_id         INTEGER,
    verifier_id         INTEGER NOT NULL,
    field_name          TEXT,
    original_value       TEXT,
    corrected_value       TEXT,
    verification_status   TEXT DEFAULT 'confirmed' CHECK(verification_status IN ('confirmed','corrected')),
    timestamp             TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prescription_id) REFERENCES prescriptions(prescription_id),
    FOREIGN KEY (verifier_id) REFERENCES users(user_id)
);
