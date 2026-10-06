-- Rates use eligible index discharges only: non-expired, and discharged at
-- least 30 days before the extract end.
SELECT
  COUNT(*) AS index_discharges,
  ROUND(AVG(los_days), 2) AS avg_los_days,
  ROUND(AVG(charges), 2) AS avg_charges,
  ROUND(100.0 * AVG(readmit_30d), 2) AS readmit_rate_pct
FROM fact_encounter
WHERE eligible_index = 1;

SELECT
  d.diagnosis_name,
  d.diagnosis_group,
  COUNT(*) AS discharges,
  ROUND(AVG(f.los_days), 2) AS avg_los_days,
  ROUND(100.0 * AVG(f.readmit_30d), 2) AS readmit_rate_pct,
  ROUND(AVG(f.charges), 2) AS avg_charges
FROM fact_encounter f
JOIN dim_diagnosis d ON d.diagnosis_sk = f.diagnosis_sk
WHERE f.eligible_index = 1
GROUP BY d.diagnosis_name, d.diagnosis_group
ORDER BY readmit_rate_pct DESC;
