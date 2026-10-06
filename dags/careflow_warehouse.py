"""Airflow wrapper around the same load the Docker pipeline runs."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from airflow import DAG
from airflow.operators.bash import BashOperator

ROOT = Path("/opt/airflow")
if not ROOT.exists():
    ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

with DAG(
    dag_id="careflow_warehouse",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
) as dag:
    extract = BashOperator(
        task_id="extract",
        bash_command=f"python {ROOT / 'src' / 'generate_raw.py'}",
    )
    load = BashOperator(
        task_id="load_transform_checks",
        bash_command=f"python {ROOT / 'src' / 'pipeline.py'}",
        env={"PYTHONPATH": str(ROOT / "src"), "DATABASE_URL": "postgresql://careflow:careflow@postgres:5432/careflow"},
    )
    extract >> load
