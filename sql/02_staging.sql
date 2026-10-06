-- Staging: typed encounter extract. Python has already coerced timestamps and charges.
-- This layer applies business rejection rules and keeps one row per encounter_id.

DROP TABLE IF EXISTS stg_patient;
CREATE TABLE stg_patient AS
SELECT
  patient_id,
  MIN(birth_date) AS birth_date,
  MIN(
    CASE LOWER(TRIM(sex))
      WHEN 'f' THEN 'F'
      WHEN 'female' THEN 'F'
      WHEN 'm' THEN 'M'
      WHEN 'male' THEN 'M'
      ELSE NULL
    END
  ) AS sex,
  NULLIF(MIN(TRIM(city)), '') AS city,
  NULLIF(MIN(TRIM(state)), '') AS state
FROM raw_patients
WHERE patient_id IS NOT NULL
GROUP BY patient_id;

DROP TABLE IF EXISTS stg_encounter_scored;
CREATE TABLE stg_encounter_scored AS
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
    WHEN ROW_NUMBER() OVER (
      PARTITION BY e.encounter_id
      ORDER BY e.source_row
    ) > 1 THEN 'duplicate_encounter_id'
    ELSE NULL
  END AS reject_reason
FROM raw_encounters_typed e
LEFT JOIN stg_patient p ON p.patient_id = e.patient_id;

DROP TABLE IF EXISTS quarantine_encounter;
CREATE TABLE quarantine_encounter AS
SELECT encounter_id, patient_id, reject_reason, charges, diagnosis_code, payer_name
FROM stg_encounter_scored
WHERE reject_reason IS NOT NULL;

DROP TABLE IF EXISTS stg_encounter;
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
  ROUND((julianday(discharge_ts) - julianday(admit_ts)), 2) AS los_days
FROM stg_encounter_scored
WHERE reject_reason IS NULL;
