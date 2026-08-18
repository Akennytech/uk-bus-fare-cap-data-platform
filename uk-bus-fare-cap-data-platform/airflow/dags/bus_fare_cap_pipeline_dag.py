"""Orchestrates the end-to-end Bronze -> Silver -> Gold pipeline.

Week 4 of the roadmap: get this DAG running against the ingestion scripts and
Spark jobs already in the repo, then extend one task at a time as each layer
is built out.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "kehinde",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="bus_fare_cap_pipeline",
    description="Bronze -> Silver -> Gold pipeline for the UK £2 bus fare cap platform",
    default_args=default_args,
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["bus-fare-cap", "portfolio"],
) as dag:

    ingest_naptan = BashOperator(
        task_id="ingest_naptan",
        bash_command="python {{ var.value.get('repo_root', '/opt/airflow/project') }}/ingestion/naptan_ingest.py",
    )

    ingest_bods = BashOperator(
        task_id="ingest_bods",
        bash_command="python {{ var.value.get('repo_root', '/opt/airflow/project') }}/ingestion/bods_ingest.py",
    )

    ingest_weather = BashOperator(
        task_id="ingest_open_meteo",
        bash_command="python {{ var.value.get('repo_root', '/opt/airflow/project') }}/ingestion/open_meteo_ingest.py",
    )

    clean_naptan_silver = BashOperator(
        task_id="clean_naptan_silver",
        bash_command="spark-submit {{ var.value.get('repo_root', '/opt/airflow/project') }}/spark/clean_naptan.py",
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=(
            "cd {{ var.value.get('repo_root', '/opt/airflow/project') }}/warehouse && "
            "dbt run --profiles-dir ."
        ),
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=(
            "cd {{ var.value.get('repo_root', '/opt/airflow/project') }}/warehouse && "
            "dbt test --profiles-dir ."
        ),
    )

    [ingest_naptan, ingest_bods, ingest_weather] >> clean_naptan_silver >> dbt_run >> dbt_test
