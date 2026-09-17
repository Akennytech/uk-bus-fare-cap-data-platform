"""Orchestrates the end-to-end Bronze -> Silver -> Gold pipeline.

Ingests six sources (NaPTAN, BODS, weather, ONS population, IMD deprivation,
fuel prices), cleans each with PySpark, loads the cleaned output into the
Postgres silver schema, then runs dbt to build the gold star schema.

Runs inside the `airflow` service defined in docker/docker-compose.yml, which
mounts the whole repo at /opt/airflow/project. Pipeline dependencies live in
their own venv at /opt/project-venv (see docker/airflow.Dockerfile), kept
separate from Airflow's own Python environment.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from airflow.operators.bash import BashOperator

from airflow import DAG

REPO_ROOT = "/opt/airflow/project"
VENV_ACTIVATE = "source /opt/project-venv/bin/activate"


def run(script: str) -> str:
    """Build the bash command to run one project script inside its venv."""
    return f"{VENV_ACTIVATE} && cd {REPO_ROOT} && python {script}"


default_args = {
    "owner": "kehinde",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

SOURCES = {
    "naptan": ("ingestion/naptan_ingest.py", "spark/clean_naptan.py", "warehouse/load_naptan_silver.py"),
    "bods": ("ingestion/bods_ingest.py", "spark/clean_bods.py", "warehouse/load_bods_silver.py"),
    "weather": ("ingestion/weather_ingest.py", "spark/clean_weather.py", "warehouse/load_weather_silver.py"),
    "ons": ("ingestion/ons_ingest.py", "spark/clean_ons.py", "warehouse/load_ons_silver.py"),
    "imd": ("ingestion/imd_ingest.py", "spark/clean_imd.py", "warehouse/load_imd_silver.py"),
    "fuel": ("ingestion/fuel_ingest.py", "spark/clean_fuel.py", "warehouse/load_fuel_silver.py"),
}

with DAG(
    dag_id="bus_fare_cap_pipeline",
    description="Bronze -> Silver -> Gold pipeline for the UK £2 bus fare cap platform",
    default_args=default_args,
    schedule="@daily",
    start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    tags=["bus-fare-cap", "portfolio"],
    max_active_runs=1,
) as dag:

    load_tasks = []

    for name, (ingest_script, clean_script, load_script) in SOURCES.items():
        ingest = BashOperator(task_id=f"ingest_{name}", bash_command=run(ingest_script))
        clean = BashOperator(task_id=f"clean_{name}", bash_command=run(clean_script))
        load = BashOperator(task_id=f"load_{name}_silver", bash_command=run(load_script))
        ingest >> clean >> load
        load_tasks.append(load)

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"{VENV_ACTIVATE} && cd {REPO_ROOT}/warehouse && dbt run --profiles-dir .",
    )
    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"{VENV_ACTIVATE} && cd {REPO_ROOT}/warehouse && dbt test --profiles-dir .",
    )

    load_tasks >> dbt_run >> dbt_test
