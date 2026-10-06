# CareFlow — Hospital Encounter Warehouse

End-to-end ELT on synthetic hospital encounters. Raw CSV extracts are typed, rejected rows are quarantined, and accepted encounters land in a star schema. Metrics are SQL, not a notebook.

This is fake data (seed 42). Do not describe the readmission rates as real clinical findings. The pattern is in the extract; the pipeline is what you are demonstrating.

## What a reviewer can run

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 src/generate_raw.py
python3 src/pipeline.py
```

That rebuilds `data/careflow.db` from scratch. A second run deletes the database and reloads, so the load is idempotent. `output/metrics.json` is rewritten each run.

`docker compose up -d` starts PostgreSQL 16 (`careflow` / `careflow`, database `careflow`) if you want the same raw files in the database already on your resume. The verified SQL in this repo uses SQLite date functions (`julianday`). Say that in an interview instead of claiming the transforms already run on Postgres.

## Model

Grain of `fact_encounter` is one accepted encounter.

- `dim_patient` — one row per patient after sex and blank-city cleanup
- `dim_diagnosis` — code, name, chapter group
- `dim_payer` — Medicare, Medicaid, Commercial, Self-pay after case folding
- `fact_encounter` — length of stay, charges, `readmit_30d`
- `quarantine_encounter` — rejected raw rows and the reason

`readmit_30d` is 1 when the next accepted encounter for that patient starts after discharge and within 30 days. Expired discharges are not index events. Same-day overlaps do not count. This is not CMS methodology.

## Verified run (seed 42)

| Step | Rows |
| --- | --- |
| Raw patients | 3,880 |
| Raw encounter rows | 7,127 |
| Fact encounters | 6,329 |
| Quarantined | 798 |

Index discharges: 5,287. Average LOS: 6.62 days. 30-day readmission: 9.34%.

Highest readmission in this extract: COPD 20.86%, sepsis 19.56%, heart failure 18.26%. AMI stays long (7.40 days) but readmits at 2.37%. That split is the point of the metric: length of stay and readmission answer different questions.

Rejection mix: orphan patient 226, missing discharge 200, unknown diagnosis 189, duplicate encounter id 97, discharge before admit 54, invalid charges 32. Checks in `sql/04_checks.sql` all return 0 on the fact table.

## Resume

**CareFlow — Hospital Encounter Warehouse** | Python, SQL, SQLite

- Built a full-refresh ELT pipeline on 7,127 synthetic encounter rows: typed extract, quarantine, and a star schema (`fact_encounter`, patient, diagnosis, payer).
- Defined length of stay and a 30-day readmission flag in SQL with window functions; index readmission was 9.34% across 5,287 non-expired discharges.
- Quarantined 798 rows (missing discharge, orphan patients, duplicate keys, invalid charges) and blocked promotion unless fact-table integrity checks returned zero.

GitHub link goes on the title line once the repo is public.
