# 0001. Technology stack

Date: 26 October 2026
Status: accepted

## Context

The platform ingests four sanctions lists daily (UN, OFAC SDN, UK Sanctions List, NIGSAC). Total volume is tens of megabytes per day. It must run on a Windows laptop and in GitHub Actions at zero cost, and demonstrate tested, documented, history-preserving data engineering.

## Decision

| Component | Resolved version | Reason |
|---|---|---|
| Python | 3.12.13 | Pinned via `.python-version`; uv manages the interpreter so builds are reproducible on Windows and in CI. |
| uv | 0.11.12 | Fast resolver, committed `uv.lock`, native Windows support. |
| DuckDB | 2.0.0 | Single-file warehouse, zero cost, strong Parquet support, runs on a laptop and in Actions. |
| dbt-core | 1.12.6 | Standard for tested, documented SQL transformations; snapshots give history without custom code. |
| dbt-duckdb | 1.11.0 | DuckDB adapter for dbt. |
| Dagster | 1.13.26 | Asset-based orchestration shows lineage, surfaces dbt tests as asset checks, runs locally with one command. |
| dagster-dbt | 0.29.26 | Loads dbt models as Dagster assets. |

Supporting libraries: httpx (HTTP), tenacity (retries), lxml (XML), selectolax (NIGSAC HTML), rapidfuzz (fuzzy matching), polars and pyarrow (Parquet), FastAPI and pydantic (API), Jinja2 (dashboard), pytest, ruff, xmlschema and respx (development). Exact versions of every package are in `uv.lock`.

The project uses a `src/` layout built with hatchling, so `sanctions_platform` is importable in tests and by Dagster without path manipulation.

## Not used in version 1

Kafka, Spark, Airflow, Iceberg and paid cloud services. The data volume does not justify them. Iceberg is a Phase 10 option.

## Consequences

Packages are not upgraded mid build without a new decision record. DuckDB allows one writer at a time, so the Dagster UI must be stopped before running dbt by hand against the same database file.
