-- Raw landing tables. Python loads CSVs here. SQL does not parse currency strings.

DROP TABLE IF EXISTS raw_patients;
CREATE TABLE raw_patients (
  patient_id text,
  birth_date text,
  sex text,
  city text,
  state text
);

DROP TABLE IF EXISTS raw_encounters;
CREATE TABLE raw_encounters (
  encounter_id text,
  patient_id text,
  admit_ts text,
  discharge_ts text,
  diagnosis_code text,
  payer text,
  department text,
  total_charges text,
  admission_type text,
  discharge_status text
);

DROP TABLE IF EXISTS raw_encounters_typed;
CREATE TABLE raw_encounters_typed (
  encounter_id text,
  patient_id text,
  admit_ts timestamp,
  discharge_ts timestamp,
  diagnosis_code text,
  payer_name text,
  department text,
  admission_type text,
  discharge_status text,
  charges numeric,
  source_row integer
);
