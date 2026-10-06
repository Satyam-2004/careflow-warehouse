-- Metric used on the resume: 30-day readmission among non-expired discharges.
SELECT
  COUNT(*) AS index_discharges,
  ROUND(AVG(los_days), 2) AS avg_los_days,
  ROUND(AVG(charges), 2) AS avg_charges,
  ROUND(100.0 * AVG(readmit_30d), 2) AS readmit_rate_pct
FROM fact_encounter
WHERE LOWER(discharge_status) != 'expired';

SELECT
  d.diagnosis_name,
  d.diagnosis_group,
  COUNT(*) AS discharges,
  ROUND(AVG(f.los_days), 2) AS avg_los_days,
  ROUND(100.0 * AVG(f.readmit_30d), 2) AS readmit_rate_pct,
  ROUND(AVG(f.charges), 2) AS avg_charges
FROM fact_encounter f
JOIN dim_diagnosis d ON d.diagnosis_sk = f.diagnosis_sk
WHERE LOWER(f.discharge_status) != 'expired'
GROUP BY d.diagnosis_name, d.diagnosis_group
ORDER BY readmit_rate_pct DESC;
