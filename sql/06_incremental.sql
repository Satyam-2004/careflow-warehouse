-- Incremental load. Staging is still rebuilt from the current raw batch.
-- Accepted encounters are inserted only when that encounter_id is not already
-- in fact_encounter. This is not a change-data capture feed.

INSERT INTO fact_encounter (
  encounter_sk,
  encounter_id,
  patient_sk,
  diagnosis_sk,
  payer_sk,
  admit_ts,
  discharge_ts,
  department,
  admission_type,
  discharge_status,
  los_days,
  charges,
  eligible_index,
  readmit_30d
)
SELECT
  (SELECT COALESCE(MAX(encounter_sk), 0) FROM fact_encounter) + ROW_NUMBER() OVER (ORDER BY s.encounter_id),
  s.encounter_id,
  p.patient_sk,
  d.diagnosis_sk,
  pay.payer_sk,
  s.admit_ts,
  s.discharge_ts,
  s.department,
  s.admission_type,
  s.discharge_status,
  s.los_days,
  s.charges,
  0,
  0
FROM stg_encounter s
JOIN dim_patient p ON p.patient_id = s.patient_id
JOIN dim_diagnosis d ON d.diagnosis_code = s.diagnosis_code
JOIN dim_payer pay ON pay.payer_name = s.payer_name
WHERE NOT EXISTS (
  SELECT 1 FROM fact_encounter f WHERE f.encounter_id = s.encounter_id
);
