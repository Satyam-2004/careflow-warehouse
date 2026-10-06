-- Staging. Rejection rules run before dedup.
-- Duplicate ranking is computed only inside otherwise-valid rows, so a clean
-- copy is kept when the earlier copy failed another check.

DROP TABLE IF EXISTS stg_patient CASCADE;
CREATE TABLE stg_patient AS
SELECT
  patient_id,
  MIN(birth_date) AS birth_date,
  MIN(
    CASE LOWER(BTRIM(sex))
      WHEN 'f' THEN 'F'
      WHEN 'female' THEN 'F'
      WHEN 'm' THEN 'M'
      WHEN 'male' THEN 'M'
      ELSE NULL
    END
  ) AS sex,
  NULLIF(MIN(BTRIM(city)), '') AS city,
  NULLIF(MIN(BTRIM(state)), '') AS state
FROM raw_patients
WHERE patient_id IS NOT NULL
GROUP BY patient_id;

DROP TABLE IF EXISTS stg_encounter_scored CASCADE;
CREATE TABLE stg_encounter_scored AS
WITH ruled AS (
  SELECT
    e.encounter_id,
    e.patient_id,
    e.admit_ts,
    e.discharge_ts,
    e.diagnosis_code,
    e.payer_name,
    e.department,
    e.admission_type,
    e.discharge_status,
    e.charges,
    e.source_row,
    CASE
      WHEN e.admit_ts IS NULL THEN 'missing_admit'
      WHEN p.patient_id IS NULL THEN 'orphan_patient'
      WHEN e.discharge_ts IS NULL THEN 'missing_discharge'
      WHEN e.discharge_ts < e.admit_ts THEN 'discharge_before_admit'
      WHEN e.charges IS NULL OR e.charges < 0 THEN 'invalid_charges'
      WHEN e.diagnosis_code IS NULL THEN 'unknown_diagnosis'
      WHEN e.payer_name IS NULL THEN 'unknown_payer'
      ELSE NULL
    END AS base_reason
  FROM raw_encounters_typed e
  LEFT JOIN stg_patient p ON p.patient_id = e.patient_id
)
SELECT
  ruled.*,
  CASE
    WHEN base_reason IS NOT NULL THEN base_reason
    WHEN ROW_NUMBER() OVER (
      PARTITION BY encounter_id, (base_reason IS NULL)
      ORDER BY source_row
    ) > 1 THEN 'duplicate_encounter_id'
    ELSE NULL
  END AS reject_reason
FROM ruled;

DROP TABLE IF EXISTS quarantine_encounter CASCADE;
CREATE TABLE quarantine_encounter AS
SELECT encounter_id, patient_id, reject_reason, charges, diagnosis_code, payer_name
FROM stg_encounter_scored
WHERE reject_reason IS NOT NULL;

DROP TABLE IF EXISTS stg_encounter CASCADE;
CREATE TABLE stg_encounter AS
SELECT
  encounter_id,
  patient_id,
  admit_ts,
  discharge_ts,
  diagnosis_code,
  payer_name,
  department,
  admission_type,
  discharge_status,
  charges,
  ROUND(EXTRACT(EPOCH FROM (discharge_ts - admit_ts)) / 86400.0, 2) AS los_days
FROM stg_encounter_scored
WHERE reject_reason IS NULL;
