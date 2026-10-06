"""Load raw CSVs into Postgres, then run the SQL warehouse.

Full refresh is the default. --incremental reloads the current raw batch and
recomputes facts for encounter ids already present, instead of dropping the
database. Readmission flags are always recomputed, because they depend on the
next encounter.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import psycopg
from psycopg.rows import dict_row

from cleaners import clean_code, clean_payer, parse_money

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
SQL = ROOT / "sql"
OUT = ROOT / "output"
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://careflow:careflow@localhost:5432/careflow",
)


def split_sql(text: str) -> list[str]:
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        lines.append(line)
    return [part.strip() for part in "\n".join(lines).split(";") if part.strip()]

def run_file(conn: psycopg.Connection, name: str) -> None:
    for statement in split_sql((SQL / name).read_text()):
        conn.execute(statement)
    conn.commit()


def load_raw(conn: psycopg.Connection) -> None:
    run_file(conn, "01_raw.sql")
    patients = pd.read_csv(RAW / "patients.csv", dtype=str).fillna("")
    encounters = pd.read_csv(RAW / "encounters.csv", dtype=str).fillna("")
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO raw_patients (patient_id, birth_date, sex, city, state)
            VALUES (%s, %s, %s, %s, %s)
            """,
            patients[["patient_id", "birth_date", "sex", "city", "state"]].itertuples(index=False, name=None),
        )
        cur.executemany(
            """
            INSERT INTO raw_encounters (
              encounter_id, patient_id, admit_ts, discharge_ts, diagnosis_code,
              payer, department, total_charges, admission_type, discharge_status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            encounters[
                [
                    "encounter_id",
                    "patient_id",
                    "admit_ts",
                    "discharge_ts",
                    "diagnosis_code",
                    "payer",
                    "department",
                    "total_charges",
                    "admission_type",
                    "discharge_status",
                ]
            ].itertuples(index=False, name=None),
        )
        typed = []
        for source_row, row in encounters.iterrows():
            admit = pd.to_datetime(row["admit_ts"], errors="coerce")
            discharge = pd.to_datetime(row["discharge_ts"], errors="coerce")
            typed.append(
                (
                    str(row["encounter_id"]),
                    str(row["patient_id"]),
                    None if pd.isna(admit) else admit.to_pydatetime(),
                    None if pd.isna(discharge) else discharge.to_pydatetime(),
                    clean_code(row["diagnosis_code"]),
                    clean_payer(row["payer"]),
                    str(row["department"]).strip(),
                    str(row["admission_type"]).strip().title(),
                    str(row["discharge_status"]).strip(),
                    parse_money(row["total_charges"]),
                    int(source_row),
                )
            )
        cur.executemany(
            """
            INSERT INTO raw_encounters_typed (
              encounter_id, patient_id, admit_ts, discharge_ts, diagnosis_code,
              payer_name, department, admission_type, discharge_status, charges, source_row
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            typed,
        )
    conn.commit()


def write_report(conn: psycopg.Connection) -> None:
    checks = conn.execute((SQL / "04_checks.sql").read_text()).fetchall()
    failed = [row for row in checks if row["value"] != 0]
    statements = split_sql((SQL / "05_metrics.sql").read_text())
    summary = conn.execute(statements[0]).fetchone()
    by_dx = conn.execute(statements[1]).fetchall()
    rejects = conn.execute(
        """
        SELECT reject_reason, COUNT(*) AS rows
        FROM quarantine_encounter
        GROUP BY reject_reason
        ORDER BY rows DESC
        """
    ).fetchall()
    counts = {
        "raw_patients": conn.execute("SELECT COUNT(*) AS n FROM raw_patients").fetchone()["n"],
        "raw_encounter_rows": conn.execute("SELECT COUNT(*) AS n FROM raw_encounters").fetchone()["n"],
        "fact_encounters": conn.execute("SELECT COUNT(*) AS n FROM fact_encounter").fetchone()["n"],
        "quarantine_rows": conn.execute("SELECT COUNT(*) AS n FROM quarantine_encounter").fetchone()["n"],
        "eligible_index": conn.execute(
            "SELECT COUNT(*) AS n FROM fact_encounter WHERE eligible_index = 1"
        ).fetchone()["n"],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    payload = {
        "counts": counts,
        "checks": checks,
        "summary": summary,
        "by_diagnosis": by_dx,
        "reject_reasons": rejects,
        "note": "HF, COPD, and sepsis follow-up gaps are planted in generate_raw.py to validate the flag.",
    }
    (OUT / "metrics.json").write_text(json.dumps(payload, indent=2, default=str))
    print(json.dumps({"counts": counts, "checks": checks, "summary": summary}, indent=2, default=str))
    if failed:
        raise SystemExit(f"checks failed: {failed}")


def main() -> None:
    if not (RAW / "encounters.csv").exists():
        raise SystemExit("Missing raw files. Run src/generate_raw.py first.")
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        load_raw(conn)
        run_file(conn, "02_staging.sql")
        # Facts are rebuilt on every run. The readmission flag depends on the
        # next encounter, so an insert-only load would leave it stale.
        run_file(conn, "03_marts.sql")
        write_report(conn)


if __name__ == "__main__":
    main()
