FROM apache/airflow:2.9.0-python3.11

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends openjdk-17-jre-headless procps python3-venv \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH="${JAVA_HOME}/bin:${PATH}"

# Project dependencies (pyspark, pandas, dbt, boto3, ...) live in their own
# venv, completely separate from Airflow's own Python environment — this
# means they can never conflict with Airflow's pinned versions (e.g. it
# wants pandas==2.1.4, we want pandas>=2.2 — no longer a problem).
COPY requirements.txt /tmp/requirements.txt
RUN python3 -m venv /opt/project-venv \
    && /opt/project-venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/project-venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt \
    && chown -R airflow:root /opt/project-venv

USER airflow
