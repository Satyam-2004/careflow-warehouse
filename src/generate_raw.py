"""Generate messy synthetic hospital extracts for the CareFlow warehouse.

Rows are fake. Defects are intentional: duplicate keys, missing discharges,
orphan patients, dirty codes, and currency strings.

The shorter follow-up gap for heart failure, COPD, and sepsis is planted.
It exists so a correct 30-day flag surfaces a known pattern. It is not a
clinical finding. AMI also gets a longer stay by construction.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
SEED = 42
ORIGIN = datetime(2023, 1, 1)
END = datetime(2026, 6, 30)

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
PAYERS = ["PM-JAY", "CGHS", "ESIC", "Private insurance", "Self-pay"]
DIRTY_PAYERS = ["pm-jay", "PMJAY", "cghs", "ESIC", "private", "self pay"]
DEPARTMENTS = ["Cardiology", "Medicine", "Pulmonology", "Nephrology", "Surgery"]
SEXES = ["F", "M", "Female", "Male", "f", "m"]
CITIES = {
    "Pune": "MH",
    "Mumbai": "MH",
    "Jaipur": "RJ",
    "Delhi": "DL",
    "Indore": "MP",
}


def main() -> None:
    random.seed(SEED)
    RAW.mkdir(parents=True, exist_ok=True)

    patients = []
    for pid in range(1, 4001):
        city = random.choice(list(CITIES) + [""])
        patients.append(
            {
                "patient_id": pid,
                "birth_date": (ORIGIN - timedelta(days=random.randint(18 * 365, 90 * 365))).date().isoformat(),
                "sex": random.choice(SEXES),
                "city": city,
                "state": CITIES.get(city, ""),
            }
        )
    patient_df = pd.DataFrame(patients).sample(frac=0.97, random_state=SEED)
    patient_df.to_csv(RAW / "patients.csv", index=False)

    rows = []
    encounter_id = 100000
    for pid in range(1, 4001):
        n_visits = random.choices([1, 2, 3, 4, 5], weights=[0.55, 0.25, 0.12, 0.06, 0.02])[0]
        cursor = ORIGIN + timedelta(days=random.randint(0, 400))
        for _ in range(n_visits):
            if cursor > END:
                break
            los = random.choices(
                [1, 2, 3, 4, 5, 7, 10, 14, 21],
                weights=[8, 14, 16, 16, 14, 12, 10, 6, 4],
            )[0]
            code = random.choice(list(DIAGNOSES))
            if code in {"I50.9", "I21.9", "A41.9", "J44.1"}:
                los += random.randint(0, 4)
            admit = cursor
            discharge = admit + timedelta(days=los)
            if discharge > END:
                break
            charges = round(random.uniform(12000, 180000) * (1 + los / 20), 2)
            payer = random.choice(PAYERS if random.random() > 0.2 else DIRTY_PAYERS)
            rows.append(
                {
                    "encounter_id": encounter_id,
                    "patient_id": pid,
                    "admit_ts": admit.strftime("%Y-%m-%d %H:%M:%S"),
                    "discharge_ts": discharge.strftime("%Y-%m-%d %H:%M:%S"),
                    "diagnosis_code": code if random.random() > 0.04 else random.choice(["", "UNKNOWN", code.lower()]),
                    "payer": payer,
                    "department": random.choice(DEPARTMENTS),
                    "total_charges": f"{charges:,.2f}" if random.random() > 0.08 else str(charges),
                    "admission_type": random.choice(["Emergency", "Elective", "Urgent", "emergency"]),
                    "discharge_status": random.choice(["Home", "SNF", "Expired", "AMA", "Home", "Home"]),
                }
            )
            encounter_id += 1
            # Planted: HF, COPD, and sepsis return sooner so the flag can be checked.
            if code in {"I50.9", "J44.1", "A41.9"}:
                gap = random.choices([12, 21, 40, 120], weights=[0.22, 0.28, 0.28, 0.22])[0]
            else:
                gap = random.choices([25, 60, 120, 240], weights=[0.08, 0.22, 0.40, 0.30])[0]
            cursor = discharge + timedelta(days=gap)

    enc = pd.DataFrame(rows)
    dupes = enc.sample(frac=0.015, random_state=SEED).copy()
    dupes["total_charges"] = dupes["total_charges"].astype(str) + "0"
    missing_idx = enc.sample(frac=0.03, random_state=7).index
    enc.loc[missing_idx, "discharge_ts"] = ""
    bad_idx = enc.sample(frac=0.008, random_state=11).index
    enc.loc[bad_idx, "discharge_ts"] = "2022-12-01 00:00:00"
    neg_idx = enc.sample(frac=0.005, random_state=13).index
    enc.loc[neg_idx, "total_charges"] = "-1500.00"

    dirty = pd.concat([enc, dupes], ignore_index=True)
    dirty.to_csv(RAW / "encounters.csv", index=False)
    print(
        f"patients={len(patient_df)} encounters={len(dirty)} "
        f"unique_ids={dirty['encounter_id'].nunique()} end={END.date().isoformat()}"
    )


if __name__ == "__main__":
    main()
