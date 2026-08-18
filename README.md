# UK £2 Bus Fare Cap — Data Engineering Platform

A free, locally-runnable data engineering platform that ingests real UK government and
open transport data to analyse the impact of the £2 single bus fare cap (England outside
London, 1 Jan – 31 Dec 2027).

Full project plan, architecture rationale, data model and roadmap:
see `UK_Bus_Fare_Cap_Project_Plan.docx` (delivered alongside this repo).

## Why this project

The UK Government on the 22nd of July 2026 confirmed a £2 cap on single bus fares across England outside
London from January 2027, backed by £400m of funding, replacing the existing £3 cap
(source: https://www.gov.uk/government/speeches/2-bus-fares-from-january-2027). This
platform ingests, cleans, models and visualises real transport, population, deprivation,
weather and fuel-price data to answer:

- Which regions benefit most from the cap?
- How much could commuters save?
- Which areas remain underserved despite lower fares?
- Which operators/routes are busiest, and how reliable are they?
- What's the potential environmental upside of a car-to-bus shift?

## Architecture

Medallion pattern (Bronze → Silver → Gold), built entirely on free/open-source tooling —
no Azure subscription or trial required:

| Layer | Tool |
|---|---|
| Object storage (Bronze/Silver) | MinIO (S3-compatible, Docker) |
| Processing | PySpark (local mode) |
| Orchestration | Apache Airflow (Docker) |
| Transformation / testing | dbt-core |
| Warehouse (Gold) | PostgreSQL (Docker) |
| Data quality | Great Expectations + dbt tests |
| BI | Power BI Desktop |
| CI/CD | GitHub Actions |

See `architecture/architecture_diagram.png` and `architecture/star_schema_diagram.png`.

## Repository layout

```
uk-bus-fare-cap-data-platform/
├── .github/workflows/     CI: lint, dbt test, docker build
├── docker/                docker-compose.yml, service config
├── ingestion/             Python API clients (BODS, NaPTAN, ONS, Open-Meteo, fuel prices)
├── bronze/                raw landing notes / MinIO bucket policies
├── spark/                 PySpark cleaning & silver-layer jobs
├── warehouse/             dbt-core project (models, tests) -> gold layer
├── sql/                   DDL for the star schema
├── airflow/dags/          DAG definitions orchestrating the pipeline
├── great_expectations/    data quality suite notes
├── dashboards/            Power BI .pbix files + screenshots (add your own)
├── tests/                 unit tests for ingestion & transformation code
├── documentation/         data dictionary, ADRs
├── architecture/          diagrams
├── .env.example
├── requirements.txt
└── README.md
```

## Getting started

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) (free for
   personal use) and Python 3.11+.
2. `cp .env.example .env` and fill in your free BODS API key from
   https://www.bus-data.dft.gov.uk/ (registration is free).
3. `cd docker && docker compose up -d` — starts PostgreSQL and MinIO.
   (Airflow is included as a commented-out block; uncomment once your DAGs are ready —
   see `docker/docker-compose.yml` for notes.)
4. `python -m venv .venv && source .venv/bin/activate` (or `.venv\Scripts\activate` on
   Windows), then `pip install -r requirements.txt`.
5. Run an ingestion script manually to smoke-test, e.g.
   `python ingestion/naptan_ingest.py`.
6. Apply the warehouse DDL: `psql -h localhost -U postgres -d bus_fare_cap -f sql/ddl_star_schema.sql`
   (or run the equivalent dbt models once the dbt project is filled out).
7. Open MinIO console at http://localhost:9001 (default credentials in `.env.example`)
   to confirm bronze/silver buckets are populating.
8. Connect Power BI Desktop to the PostgreSQL gold schema
   (`localhost:5432`, database `bus_fare_cap`) and start building dashboards.

## Data sources (all free)

| Source | Provides | Link |
|---|---|---|
| Bus Open Data Service (BODS) | Timetables, live vehicle positions, fares | bus-data.dft.gov.uk |
| NaPTAN | Bus stop locations | naptan.dft.gov.uk |
| DfT Bus Statistics | Patronage, fares, punctuality | gov.uk/government/collections/bus-statistics |
| ONS Population Estimates | Population by local authority | ons.gov.uk |
| English Indices of Deprivation 2019 | Deprivation by LSOA | gov.uk |
| Open-Meteo | Historical/forecast weather, no key required | open-meteo.com |
| DfT Weekly Road Fuel Prices | National average pump prices | gov.uk/government/statistics/weekly-road-fuel-prices |

## Data limitations

England does not publish open ticket-level bus patronage data. This platform models
passenger demand as a **service-level proxy** (scheduled trips) combined with published
aggregate DfT patronage statistics — not true smart-ticketing volumes. Cost-of-living
and CO₂ figures are clearly-labelled, documented **scenario estimates**, kept in
separate fact tables from directly-sourced data. See the full plan document for detail.

## Status

This is a starter scaffold: folder structure, configuration, and one worked ingestion
example are in place. Follow the 8-week roadmap in the project plan document to build
out the remaining ingestion clients, Spark jobs, dbt models, DAGs and dashboards.

## License

MIT — see `LICENSE`. Data from third parties (BODS, NaPTAN, ONS, DfT, Open-Meteo)
remains subject to their own licences (mostly Open Government Licence v3.0).
