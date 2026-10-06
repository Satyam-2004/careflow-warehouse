"""Read-only view of fact_encounter. Requires the warehouse load to have finished."""

from __future__ import annotations

import os

import pandas as pd
import psycopg
import streamlit as st

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://careflow:careflow@localhost:5432/careflow",
)

st.set_page_config(page_title="CareFlow encounters", layout="wide")
st.title("CareFlow encounter warehouse")
st.caption("Synthetic India-scheme encounters. Heart failure, COPD, and sepsis gaps are planted to validate the flag.")

query = """
SELECT d.diagnosis_name,
       p.payer_name,
       f.los_days,
       f.charges,
       f.readmit_30d,
       f.eligible_index
FROM fact_encounter f
JOIN dim_diagnosis d ON d.diagnosis_sk = f.diagnosis_sk
JOIN dim_payer p ON p.payer_sk = f.payer_sk
"""
with psycopg.connect(DATABASE_URL) as conn:
    frame = pd.read_sql(query, conn)

eligible = frame[frame["eligible_index"] == 1]
left, right = st.columns(2)
left.metric("Eligible discharges", f"{len(eligible):,}")
right.metric("30-day readmission", f"{100 * eligible['readmit_30d'].mean():.2f}%")

by_dx = (
    eligible.groupby("diagnosis_name", as_index=False)
    .agg(discharges=("readmit_30d", "size"), readmit_rate=("readmit_30d", "mean"), avg_los=("los_days", "mean"))
    .sort_values("readmit_rate", ascending=False)
)
by_dx["readmit_rate"] = (100 * by_dx["readmit_rate"]).round(2)
st.subheader("Readmission by diagnosis")
st.bar_chart(by_dx.set_index("diagnosis_name")["readmit_rate"])
st.dataframe(by_dx, use_container_width=True)

st.subheader("Payer mix")
st.bar_chart(eligible.groupby("payer_name").size())
