"""Load raw CSVs, apply a typed extract, then run the SQL warehouse.

Full refresh. Re-running deletes data/careflow.db and rebuilds every table.
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
SQL = ROOT / "sql"
OUT = ROOT / "output"
DB_PATH = Path(os.environ.get("CAREFLOW_DB", ROOT / "data" / "careflow.db"))

DIAGNOSIS_NAME = {
    "I50.9": "Heart failure",
    "E11.9": "Type 2 diabetes",
    "J18.9": "Pneumonia",
    "N18.6": "End-stage renal disease",
    "I21.9": "Acute myocardial infarction",
    "J44.1": "COPD with exacerbation",
    "A41.9": "Sepsis",
    "K92.2": "GI hemorrhage",
}
PAYER_ALIASES = {
    "medicare": "Medicare",
    "medicaid": "Medicaid",
    "commercial": "Commercial",
    "self-pay": "Self-pay",
}


def parse_money(value: object) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip().replace(",", "").replace(" ", "")
    if text == "" or text.lower() == "nan":
        return None
    try:
        return round(float(text), 2)
    except ValueError:
        return None


def clean_code(value: object) -> str | None:
    text = str(value or "").strip().upper()
    if text in DIAGNOSIS_NAME:
        return text
    return None


def clean_payer(value: object) -> str | None:
    text = " ".join(str(value or "").split()).lower()
    return PAYER_ALIASES.get(text)


def run_sql(conn: sqlite3.Connection, name: str) -> None:
    conn.executescript((SQL / name).read_text())
    conn.commit()


def main() -> None:
    if not (RAW / "encounters.csv").exists():
        raise SystemExit("Missing raw files. Run src/generate_raw.py first.")
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    patients = pd.read_csv(RAW / "patients.csv", dtype=str)
    encounters = pd.read_csv(RAW / "encounters.csv", dtype=str)
    patients.to_sql("raw_patients", conn, index=False, if_exists="replace")

    typed = pd.DataFrame(
        {
            "encounter_id": encounters["encounter_id"].astype(str),
            "patient_id": encounters["patient_id"].astype(str),
            "admit_ts": pd.to_datetime(encounters["admit_ts"], errors="coerce"),
            "discharge_ts": pd.to_datetime(encounters["discharge_ts"], errors="coerce"),
            "diagnosis_code": encounters["diagnosis_code"].map(clean_code),
            "payer_name": encounters["payer"].map(clean_payer),
            "department": encounters["department"].fillna("").str.strip(),
            "admission_type": encounters["admission_type"].fillna("").str.strip().str.title(),
            "discharge_status": encounters["discharge_status"].fillna("").str.strip(),
            "charges": encounters["total_charges"].map(parse_money),
            "source_row": range(len(encounters)),
        }
    )
    typed["admit_ts"] = typed["admit_ts"].dt.strftime("%Y-%m-%d %H:%M:%S")
    typed["discharge_ts"] = typed["discharge_ts"].dt.strftime("%Y-%m-%d %H:%M:%S")
    typed.to_sql("raw_encounters_typed", conn, index=False, if_exists="replace")
    encounters.to_sql("raw_encounters", conn, index=False, if_exists="replace")

    run_sql(conn, "02_staging.sql")
    run_sql(conn, "03_marts.sql")

    checks = [dict(row) for row in conn.execute((SQL / "04_checks.sql").read_text())]
    failed = [row for row in checks if row["value"] != 0]
    summary = dict(conn.execute((SQL / "05_metrics.sql").read_text().split(";")[0]).fetchone())
    by_dx = [
        dict(row)
        for row in conn.execute((SQL / "05_metrics.sql").read_text().split(";")[1])
    ]
    rejects = [
        dict(row)
        for row in conn.execute(
            """
            SELECT reject_reason, COUNT(*) AS rows
            FROM quarantine_encounter
            GROUP BY reject_reason
            ORDER BY rows DESC
            """
        )
    ]
    counts = {
        "raw_patients": conn.execute("SELECT COUNT(*) FROM raw_patients").fetchone()[0],
        "raw_encounter_rows": conn.execute("SELECT COUNT(*) FROM raw_encounters").fetchone()[0],
        "fact_encounters": conn.execute("SELECT COUNT(*) FROM fact_encounter").fetchone()[0],
        "quarantine_rows": conn.execute("SELECT COUNT(*) FROM quarantine_encounter").fetchone()[0],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    payload = {
        "counts": counts,
        "checks": checks,
        "summary": summary,
        "by_diagnosis": by_dx,
        "reject_reasons": rejects,
    }
    (OUT / "metrics.json").write_text(json.dumps(payload, indent=2))
    print(json.dumps({"counts": counts, "checks": checks, "summary": summary}, indent=2))
    if failed:
        raise SystemExit(f"checks failed: {failed}")


if __name__ == "__main__":
    main()
