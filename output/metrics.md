# CareFlow warehouse run

Synthetic encounters, extract end 2026-06-30, no discharge after 2025-12-13 in this seed. Heart failure, COPD, and sepsis return gaps are planted so the flag can be checked. Not a clinical finding.

Eligible index discharges exclude expired stays and any discharge within 30 days of the extract end.

- Fact encounters: 6,333
- Eligible index discharges: 5,280
- 30-day readmission: 9.30%
- Average length of stay: 6.76 days

| Diagnosis | Eligible discharges | Readmission | Avg LOS |
| --- | --- | --- | --- |
| COPD with exacerbation | 623 | 21.03% | 7.49 |
| Heart failure | 707 | 19.24% | 7.56 |
| Sepsis | 683 | 19.18% | 8.06 |
| Type 2 diabetes | 671 | 3.43% | 5.96 |
| Pneumonia | 616 | 3.25% | 5.45 |
| End-stage renal disease | 613 | 2.77% | 5.91 |
| GI hemorrhage | 703 | 2.70% | 6.01 |
| Acute myocardial infarction | 664 | 2.11% | 7.48 |

`docker compose up --build pipeline` rewrites `output/metrics.json` from Postgres. The chart is `output/readmission_by_diagnosis.png`.
