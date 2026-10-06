-- Each check must return 0.
SELECT 'duplicate_encounter_ids' AS check_name, COUNT(*) AS value
FROM (
  SELECT encounter_id FROM fact_encounter GROUP BY encounter_id HAVING COUNT(*) > 1
) d
UNION ALL
SELECT 'orphan_patient', COUNT(*)
FROM fact_encounter f
LEFT JOIN dim_patient p ON p.patient_sk = f.patient_sk
WHERE p.patient_sk IS NULL
UNION ALL
SELECT 'orphan_diagnosis', COUNT(*)
FROM fact_encounter f
LEFT JOIN dim_diagnosis d ON d.diagnosis_sk = f.diagnosis_sk
WHERE d.diagnosis_sk IS NULL
UNION ALL
SELECT 'negative_los', COUNT(*)
FROM fact_encounter
WHERE los_days < 0
UNION ALL
SELECT 'null_charges', COUNT(*)
FROM fact_encounter
WHERE charges IS NULL OR charges < 0
UNION ALL
SELECT 'ineligible_readmit_flag', COUNT(*)
FROM fact_encounter
WHERE eligible_index = 0 AND readmit_30d = 1;
