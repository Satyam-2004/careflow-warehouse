-- Marts. Grain of fact_encounter is one accepted encounter.
-- readmit_30d is 1 when the next accepted encounter starts after discharge
-- and within 30 days. Expired discharges are not index events.
-- eligible_index is 0 when discharge is within 30 days of the extract end,
-- so a late stay is not treated as a non-readmission it could not yet show.

DROP TABLE IF EXISTS dim_patient CASCADE;
CREATE TABLE dim_patient AS
SELECT
  ROW_NUMBER() OVER (ORDER BY patient_id) AS patient_sk,
  patient_id,
  birth_date,
  sex,
  city,
  state
FROM stg_patient;

DROP TABLE IF EXISTS dim_payer CASCADE;
CREATE TABLE dim_payer AS
SELECT
  ROW_NUMBER() OVER (ORDER BY payer_name) AS payer_sk,
  payer_name
FROM (SELECT DISTINCT payer_name FROM stg_encounter) payers;

DROP TABLE IF EXISTS dim_diagnosis CASCADE;
CREATE TABLE dim_diagnosis AS
SELECT
  ROW_NUMBER() OVER (ORDER BY diagnosis_code) AS diagnosis_sk,
  diagnosis_code,
  CASE diagnosis_code
    WHEN 'I50.9' THEN 'Heart failure'
    WHEN 'E11.9' THEN 'Type 2 diabetes'
    WHEN 'J18.9' THEN 'Pneumonia'
    WHEN 'N18.6' THEN 'End-stage renal disease'
    WHEN 'I21.9' THEN 'Acute myocardial infarction'
    WHEN 'J44.1' THEN 'COPD with exacerbation'
    WHEN 'A41.9' THEN 'Sepsis'
    WHEN 'K92.2' THEN 'GI hemorrhage'
  END AS diagnosis_name,
  CASE SUBSTRING(diagnosis_code, 1, 1)
    WHEN 'A' THEN 'Infectious'
    WHEN 'E' THEN 'Endocrine'
    WHEN 'I' THEN 'Circulatory'
    WHEN 'J' THEN 'Respiratory'
    WHEN 'K' THEN 'Digestive'
    WHEN 'N' THEN 'Genitourinary'
  END AS diagnosis_group
FROM (SELECT DISTINCT diagnosis_code FROM stg_encounter) codes;

DROP TABLE IF EXISTS fact_encounter CASCADE;
CREATE TABLE fact_encounter AS
WITH bounds AS (
  SELECT MAX(discharge_ts) AS extract_end FROM stg_encounter
),
ordered AS (
  SELECT
    e.*,
    LEAD(e.admit_ts) OVER (
      PARTITION BY e.patient_id
      ORDER BY e.admit_ts, e.encounter_id
    ) AS next_admit_ts,
    b.extract_end
  FROM stg_encounter e
  CROSS JOIN bounds b
)
SELECT
  ROW_NUMBER() OVER (ORDER BY o.admit_ts, o.encounter_id) AS encounter_sk,
  o.encounter_id,
  p.patient_sk,
  d.diagnosis_sk,
  pay.payer_sk,
  o.admit_ts,
  o.discharge_ts,
  o.department,
  o.admission_type,
  o.discharge_status,
  o.los_days,
  o.charges,
  CASE
    WHEN LOWER(o.discharge_status) = 'expired' THEN 0
    WHEN o.discharge_ts > o.extract_end - INTERVAL '30 days' THEN 0
    ELSE 1
  END AS eligible_index,
  CASE
    WHEN LOWER(o.discharge_status) = 'expired' THEN 0
    WHEN o.discharge_ts > o.extract_end - INTERVAL '30 days' THEN 0
    WHEN o.next_admit_ts IS NULL THEN 0
    WHEN o.next_admit_ts > o.discharge_ts
     AND o.next_admit_ts <= o.discharge_ts + INTERVAL '30 days' THEN 1
    ELSE 0
  END AS readmit_30d
FROM ordered o
JOIN dim_patient p ON p.patient_id = o.patient_id
JOIN dim_diagnosis d ON d.diagnosis_code = o.diagnosis_code
JOIN dim_payer pay ON pay.payer_name = o.payer_name;

CREATE INDEX IF NOT EXISTS ix_fact_patient ON fact_encounter(patient_sk);
CREATE INDEX IF NOT EXISTS ix_fact_dx ON fact_encounter(diagnosis_sk);
CREATE INDEX IF NOT EXISTS ix_fact_payer ON fact_encounter(payer_sk);
CREATE UNIQUE INDEX IF NOT EXISTS ux_fact_encounter_id ON fact_encounter(encounter_id);
