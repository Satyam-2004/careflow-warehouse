# CareFlow encounter warehouse

Synthetic hospital encounters for a small India-scheme provider, loaded into PostgreSQL and modeled as a star schema. Cities are Pune, Mumbai, Jaipur, Delhi, and Indore. Payers are PM-JAY, CGHS, ESIC, private insurance, and self-pay.

The shorter return gap for heart failure, COPD, and sepsis is planted in `src/generate_raw.py`. A correct 30-day flag surfaces that pattern. It is a logic check, not a clinical finding. AMI stays are also lengthened in the generator.

## Run

```bash
python src/generate_raw.py
docker compose up --build pipeline
```

Postgres listens on `localhost:5432` (`careflow` / `careflow`). The pipeline container loads the CSVs, runs `sql/01_raw.sql` through `sql/05_metrics.sql`, and writes `output/metrics.json`. Without Docker, the same load is `PYTHONPATH=src python src/pipeline.py` against that URL.

The planted-pattern check on seed 42, after the 30-day censor, is 9.30% across 5,280 eligible discharges. COPD, heart failure, and sepsis sit near 19–21%. The other diagnoses sit near 2–3%. AMI still has a long stay. See `output/metrics.md` and `output/readmission_by_diagnosis.png`.

Dashboard, after the load:

```bash
docker compose --profile dashboard up dashboard
```

Airflow DAG `careflow_warehouse` is in `dags/`. It is the same extract and load, wrapped as two tasks:

```bash
docker compose --profile airflow up airflow
```

Python typing and payer cleanup happen before the database load. Staging, dedup, the star schema, and the readmission flag are SQL. That split is why the load is a hybrid, not a pure ELT job.

## Model

`fact_encounter` is one accepted encounter.

`readmit_30d` is 1 when the next accepted encounter for that patient starts after discharge and within 30 days. Expired discharges are not index events.

`eligible_index` is 0 when discharge falls within 30 days of the extract end (`MAX(discharge_ts)`). Those rows are excluded from the rate so a late stay is not counted as a non-readmission it could not yet show.

Duplicate ranking runs only over rows that already passed the other rejection rules. If the first copy is missing a discharge and a later copy is valid, the valid copy is kept.

## Checks

`sql/04_checks.sql` must return 0 for duplicate encounter ids, orphan keys, negative length of stay, invalid charges, and a readmission flag on an ineligible index.
