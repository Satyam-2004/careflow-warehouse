"""Generate messy synthetic hospital extracts for the CareFlow warehouse.

Rows are fake. Defects are intentional: duplicate keys, missing discharges,
orphan patients, dirty codes, and currency strings.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
SEED = 42

DIAGNOSES = {
    "I50.9": "Heart failure",
    "E11.9": "Type 2 diabetes",
    "J18.9": "Pneumonia",
    "N18.6": "End-stage renal disease",
    "I21.9": "Acute myocardial infarction",
    "J44.1": "COPD with exacerbation",
    "A41.9": "Sepsis",
    "K92.2": "GI hemorrhage",
}
PAYERS = ["Medicare", "Medicaid", "Commercial", "Self-pay"]
DEPARTMENTS = ["Cardiology", "Medicine", "Pulmonology", "Nephrology", "Surgery"]
SEXES = ["F", "M", "Female", "Male", "f", "m"]
CITIES = ["Pune", "Jaipur", "Mumbai", "Delhi", "Indore", ""]


def main() -> None:
    random.seed(SEED)
    RAW.mkdir(parents=True, exist_ok=True)
    origin = datetime(2023, 1, 1)

    patients = []
    for pid in range(1, 4001):
        patients.append(
            {
                "patient_id": pid,
                "birth_date": (origin - timedelta(days=random.randint(18 * 365, 90 * 365))).date().isoformat(),
                "sex": random.choice(SEXES),
                "city": random.choice(CITIES),
                "state": random.choice(["MH", "RJ", "DL", "MP", ""]),
            }
        )
    # Drop a slice so some encounters have no patient dimension row.
    patient_df = pd.DataFrame(patients).sample(frac=0.97, random_state=SEED)
    patient_df.to_csv(RAW / "patients.csv", index=False)

    rows = []
    encounter_id = 100000
    for pid in range(1, 4001):
        n_visits = random.choices([1, 2, 3, 4, 5], weights=[0.55, 0.25, 0.12, 0.06, 0.02])[0]
        cursor = origin + timedelta(days=random.randint(0, 500))
        for _ in range(n_visits):
            los = random.choices(
                [1, 2, 3, 4, 5, 7, 10, 14, 21],
                weights=[8, 14, 16, 16, 14, 12, 10, 6, 4],
            )[0]
            code = random.choice(list(DIAGNOSES))
            if code in {"I50.9", "I21.9", "A41.9", "J44.1"}:
                los += random.randint(0, 4)
            admit = cursor
            discharge = admit + timedelta(days=los)
            charges = round(random.uniform(12000, 180000) * (1 + los / 20), 2)
            rows.append(
                {
                    "encounter_id": encounter_id,
                    "patient_id": pid,
                    "admit_ts": admit.strftime("%Y-%m-%d %H:%M:%S"),
                    "discharge_ts": discharge.strftime("%Y-%m-%d %H:%M:%S"),
                    "diagnosis_code": code if random.random() > 0.04 else random.choice(["", "UNKNOWN", code.lower()]),
                    "payer": random.choice(PAYERS + ["medicare", "MEDICAID", " commercial "]),
                    "department": random.choice(DEPARTMENTS),
                    "total_charges": f"{charges:,.2f}" if random.random() > 0.08 else str(charges),
                    "admission_type": random.choice(["Emergency", "Elective", "Urgent", "emergency"]),
                    "discharge_status": random.choice(["Home", "SNF", "Expired", "AMA", "Home", "Home"]),
                }
            )
            encounter_id += 1
            if code in {"I50.9", "J44.1", "A41.9"}:
                gap = random.choices([12, 21, 40, 120], weights=[0.22, 0.28, 0.28, 0.22])[0]
            else:
                gap = random.choices([25, 60, 120, 240], weights=[0.08, 0.22, 0.40, 0.30])[0]
            cursor = discharge + timedelta(days=gap)

    enc = pd.DataFrame(rows)

    # Duplicate keys: same encounter_id, slightly different charges.
    dupes = enc.sample(frac=0.015, random_state=SEED).copy()
    dupes["total_charges"] = dupes["total_charges"].astype(str) + "0"
    # Missing discharge on a slice of rows.
    missing_idx = enc.sample(frac=0.03, random_state=7).index
    enc.loc[missing_idx, "discharge_ts"] = ""
    # Impossible stay: discharge before admit.
    bad_idx = enc.sample(frac=0.008, random_state=11).index
    enc.loc[bad_idx, "discharge_ts"] = "2022-12-01 00:00:00"
    # A few negative charge strings.
    neg_idx = enc.sample(frac=0.005, random_state=13).index
    enc.loc[neg_idx, "total_charges"] = "-1500.00"

    dirty = pd.concat([enc, dupes], ignore_index=True)
    dirty.to_csv(RAW / "encounters.csv", index=False)
    print(f"patients={len(patient_df)} encounters={len(dirty)} unique_ids={dirty['encounter_id'].nunique()}")


if __name__ == "__main__":
    main()
