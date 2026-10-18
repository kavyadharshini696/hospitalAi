
import os
import sqlite3
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app

medicine_features = Blueprint("medicine_features", __name__)


def get_db():
    folder = current_app.instance_path
    os.makedirs(folder, exist_ok=True)
    db_path = os.path.join(folder, "medicine_features.db")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS medicines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                brand TEXT NOT NULL,
                expiry_date TEXT NOT NULL
            )
        """)


@medicine_features.route("/medicine-features", methods=["GET"])
def index():
    initialize_db()

    with get_db() as conn:
        medicines = conn.execute(
            "SELECT * FROM medicines ORDER BY expiry_date"
        ).fetchall()

    today = date.today()

    medicine_list = []
    for medicine in medicines:
        item = dict(medicine)
        expiry = date.fromisoformat(item["expiry_date"])
        days_left = (expiry - today).days

        if days_left < 0:
            item["status"] = "Expired"
        elif days_left <= 30:
            item["status"] = "Expiring soon"
        else:
            item["status"] = "Valid"

        item["days_left"] = days_left
        medicine_list.append(item)

    return render_template(
        "medicine_features.html",
        medicines=medicine_list,
        today=today.isoformat()
    )


@medicine_features.route("/medicine-features/add", methods=["POST"])
def add_medicine():
    initialize_db()

    name = request.form.get("name", "").strip()
    brand = request.form.get("brand", "").strip()
    expiry_date = request.form.get("expiry_date", "").strip()

    if not name or not brand or not expiry_date:
        flash("Please fill in all medicine details.", "error")
        return redirect(url_for("medicine_features.index"))

    try:
        parsed_date = date.fromisoformat(expiry_date)
    except ValueError:
        flash("Please enter a valid expiry date.", "error")
        return redirect(url_for("medicine_features.index"))

    with get_db() as conn:
        conn.execute(
            """INSERT INTO medicines (name, brand, expiry_date)
               VALUES (?, ?, ?)""",
            (name, brand, parsed_date.isoformat())
        )

    flash("Medicine added successfully.", "success")
    return redirect(url_for("medicine_features.index"))
