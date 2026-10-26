# Sanctions List Pipeline: Build Log

Owner: Paul Adebayo (GitHub: TechPaulFrey)
Executor: Claude Code, working in Paul's Windows environment
Log started: 26 October 2026
Project name: Sanctions List Pipeline. Repository name: `sanctions-list-pipeline`. Chosen by Paul on 26 October 2026, replacing the working title Sanctions List Pipeline.

This file is the single source of truth for the build. Claude Code reads it at the start of every session, works phase by phase, ticks acceptance criteria only when they are proven, and appends to the Progress Log at the end of every session.


## 1. What we are building and why

Financial institutions in Nigeria must screen customers against both the UN Security Council Consolidated List and the Nigeria Sanctions List. Global institutions add the US OFAC list and the UK Sanctions List. Each list is published by a different authority, in a different format, on a different schedule, with different identifiers and different data quality.

This project builds a daily data platform that:

1. Fetches the four official lists every day and stores every raw file unaltered.
2. Parses them into one common model of sanctioned parties (individuals, entities, groups, vessels).
3. Keeps full history, so we can answer "who was on which list on any date, and what changed".
4. Tests data quality on every run and fails loudly when a source breaks.
5. Links the same party across lists, first by official UN reference numbers, then by fuzzy name matching.
6. Serves a screening API and a public static dashboard showing daily changes and source freshness.

It is a portfolio demonstration of production data engineering. It is not a certified screening product, and the README must say so.


## 2. Verified data sources

All URLs below were checked on 26 October 2026. Phase 1 must verify each one again before writing the fetcher and record the result in `docs/sources/<source>.md`.

### 2.1 UN Security Council Consolidated List
* URL: https://scsanctions.un.org/resources/xml/en/consolidated.xml
* Format: XML. Root element carries a `dateGenerated` attribute. Records are split into individuals and entities, each with a UN reference number such as `QDi.322` (individual) or `QDe.138` (entity).
* Cadence: regenerated nightly.
* Role in this project: the base list. UN reference numbers are the primary key for cross list linking, because the UK list and the Nigerian narratives cite them.

### 2.2 US OFAC Specially Designated Nationals (SDN) List
* Primary file for version 1: SDN.XML from the OFAC Sanctions List Service. Download links are listed at https://sanctionslist.ofac.treas.gov/Home/static/sdn.html
* Advanced format (stretch goal): https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN_ADVANCED.XML
* Latest delta file (changes since previous publication): https://sanctionslistservice.ofac.treas.gov/changes/latest
* API documentation (Word file): https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/APIDocumentation.docx
* Why SDN.XML first: it holds the same core data as the advanced file with a much simpler structure. The advanced file adds metadata useful for screening and is a Phase 10 upgrade.
* Role in this project: the largest list, and the only source that publishes its own delta file. We use that delta to reconcile our change detection.

### 2.3 UK Sanctions List (FCDO)
* XML: https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.xml
* CSV: https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.csv
* XML schema (version 4.33.3): https://assets.publishing.service.gov.uk/media/6916e72cdb01ecfcf96fc96b/SanctionsListSchema-4.33.3.xsd
* Format guide: https://www.gov.uk/guidance/format-guide-for-the-uk-sanctions-list
* Publication page: https://www.gov.uk/government/publications/the-uk-sanctions-list (last updated 26 October 2026 with 15 new Sudan regime designations)
* Licence: Open Government Licence v3.0.
* Important history: the OFSI Consolidated List closed on 28 January 2026. The UK Sanctions List is now the only UK source. Systems keyed on "OFSI Group ID" must move to the list's "Unique ID"; the old ID is retained only for parties designated before that date. Our model keys UK parties on Unique ID and keeps OFSI Group ID as a legacy column. This migration is a talking point in the README.
* Ingest plan: parse the XML as the system of record and validate it against the XSD. Fetch the CSV too and reconcile record counts between the two formats on every run.

### 2.4 Nigeria Sanctions List (NIGSAC)
* Individuals and entities list page: https://nigsac.gov.ng/IndSancList
* Detail pages: `https://nigsac.gov.ng/IndSancDetails?id=<integer>` for individuals and groups, `https://nigsac.gov.ng/EntSancDetails?id=<integer>` for entities
* Narrative press releases: https://nigsac.gov.ng/Sanctions
* Format: server rendered HTML tables. No CSV, XML or API was found. The list page shows two tables. The individuals table has columns S/N, Full Name, Reference Number, Record Date, Details link. The entities table has S/N, Entity Name, Comments, Record Date, Details link.
* Size on 26 October 2026: 54 rows in the individuals table (which also contains the six designated groups) and 15 rows in the entities table. Most recent record date: 18 June 2026.
* Copyright: the site footer states all rights reserved. See section 10 for how this limits what we republish.
* Role in this project: the hardest and most valuable source. It is small, but it is the messiest, and no screening tutorial covers it.

### 2.5 Sources deliberately excluded
* OpenSanctions bulk data: licensed CC BY NC 4.0. Compliance screening inside a for profit business counts as commercial use. Building on it would block reuse in Nexhull. We may use it only as an external benchmark in the evaluation notebook, never as an input.
* EU Consolidated Financial Sanctions List: valuable, but its download URL and access terms were not verified in this session. It is listed as a Phase 10 addition, to be verified before any code is written.


## 3. Known data quality issues in the Nigeria Sanctions List

These were observed on the live page on 26 October 2026. Each one becomes an explicit test or cleaning rule in Phase 4. Do not silently "fix" any of them; every correction is recorded in a seed file with the evidence.

1. Reused reference numbers for different people. `NLISWi.19` to `NLISWi.23` were assigned in November 2024 (for example `NLISWi.23` to RABIU IDRIS SULEIMAN) and the same numbers were assigned again in June 2026 (for example `NLISWi.23` to ABDULLAHI UMAR USMAN). Reference number alone is therefore not a unique key for this source.
2. Missing reference number with a null date. MUKTAR MUHAMMAD ADAMU (detail id 1036) has an empty reference number and a record date of `1/1/0001 12:00:00 AM`, which is a .NET default value meaning "not set". Voice of Nigeria reported his reference as `NLISWi.20` in June 2026.
3. Trailing punctuation in a reference number: `NLIPBi.14-` for OGUMU PEACE KEWE.
4. Name order differences against other publications: the list shows YAKUBU OGIRIMA IBRAHIM while Voice of Nigeria reported Ibrahim Yakubu Ogirima under the same reference `NLISWi.19`.
5. Mixed letter case: most names are upper case, some are title case (for example "Mohammed Saleh Buba").
6. Reference number embedded in a name: "YAN BINDIGA GROUP NLBDG".
7. Non standard reference formats: `NSC/03/18/AFNU`, `NSC/03/18/MS`, `NSC/02/18/AAO`.
8. Groups stored in the individuals table: JAS (Boko Haram) `NLJAS`, ANSARU `NLANS`, ISWAP `NLISW`, IPOB `NLIPB`, Yan Taadda `NLTAD`, Yan Bindiga `NLBDG`.
9. Entity rows have no reference number column. The narrative page gives entity references such as `NLJASe.12`.
10. Narrative and list disagree on entity suffixes. The narrative for Alin Yar Yaya General Enterprises cites `NLJASi.11` in one paragraph and `NLJASe.11` in the record block.
11. Diacritics and apostrophes in names: "YAN TAÁDDA GROUP", "JAMA'ATU AHLIS SUNNA LIDDA'AWATI WAL-JIHAD".
12. Record dates are local timestamps with no time zone, in US month first format.
13. Detail pages contain phone numbers, home addresses and passport numbers. See section 10.

Reference number grammar inferred from the data: `NL` + group code (`JAS`, `ANS`, `ISW`, `IPB`, `TAD`, `BDG`) + optional type letter (`i` individual, `e` entity) + optional `.` and sequence number. Phase 2 must encode this as a regular expression with tests, and route anything that does not match into a quarantine table instead of dropping it.


## 4. Architecture

Layers, from source to user:

1. Fetch. One fetcher per source. Each run downloads the file, computes a SHA256 hash, and writes it to the raw store only when the hash differs from the last stored version. Every attempt, successful or not, is written to a manifest table.
2. Raw store. Immutable files in `data/raw/<source>/<YYYY>/<MM>/<DD>/<fetched_at_utc>_<hash12>.<ext>`. Never edited, never deleted by code.
3. Parse (bronze). One parser per source turns a raw file into Parquet rows with source specific columns and full lineage (raw file path, hash, fetched_at).
4. Transform (silver and gold, in dbt on DuckDB). Staging models per source, an intermediate unified party model, history via dbt snapshots, and marts for change events, cross list links and freshness.
5. Quality. dbt tests, Dagster asset checks, and Python tests on parsers. A failed blocking check stops downstream assets.
6. Orchestration. Dagster assets for every layer, one daily schedule, retries on fetch, freshness policies per source.
7. Serving. A FastAPI screening API run locally and in the demo video, and a static dashboard built from mart exports and published on GitHub Pages.

Data flow summary: source websites → fetchers → raw store and manifest → parsers → bronze Parquet → dbt staging → unified parties → snapshots (history) → marts → API and dashboard.


## 5. Technology choices

* Python 3.12, managed with uv. Reason: fast, reproducible lock file, works natively on Windows.
* DuckDB as the warehouse. Reason: zero cost, single file, excellent Parquet and XML adjacent tooling, runs on a laptop and in GitHub Actions.
* dbt Core with the DuckDB adapter. Reason: the industry standard for tested, documented SQL transformations; snapshots give us history without custom code.
* Dagster with the dbt integration. Reason: asset based orchestration shows lineage clearly, turns dbt tests into asset checks, and runs locally with one command.
* httpx for HTTP, lxml for XML, selectolax for the NIGSAC HTML, rapidfuzz for fuzzy matching, polars and pyarrow for Parquet, FastAPI for the API, pytest and ruff for tests and linting.
* GitHub Actions for CI and the scheduled daily run. GitHub Pages for the dashboard.

Deliberately not used in version 1: Kafka, Spark, Airflow, Iceberg, any paid cloud. The data volume does not justify them, and reviewers notice decoration. Iceberg is a Phase 10 option.

Version policy: at Phase 0, install the latest stable release of each package and commit `uv.lock`. Record the resolved versions of Python, DuckDB, dbt core, the DuckDB adapter and Dagster in `docs/decisions/0001-stack.md`. Do not upgrade mid build without a new decision record.


## 6. Repository layout

```
sanctions-list-pipeline/
├── BUILD_LOG.md                  this file
├── README.md
├── pyproject.toml
├── uv.lock
├── .gitignore
├── .github/workflows/
│   ├── ci.yml                    lint, unit tests, dbt build on fixtures
│   └── daily.yml                 scheduled live run, publish dashboard
├── src/sanctions_platform/
│   ├── __init__.py
│   ├── config.py                 source URLs, paths, User Agent, timeouts
│   ├── fetch/                    one module per source plus shared http client
│   ├── parse/                    one module per source
│   ├── matching/                 normalisation, blocking, scoring
│   ├── store/                    raw store and manifest helpers
│   └── definitions.py            Dagster definitions
├── transform/                    dbt project
│   ├── dbt_project.yml
│   ├── profiles.yml
│   ├── models/staging/
│   ├── models/intermediate/
│   ├── models/marts/
│   ├── snapshots/
│   ├── seeds/
│   └── tests/
├── api/main.py                   FastAPI app
├── dashboard/                    static site generator and templates
├── analysis/                     evaluation notebook, README metric queries
├── tests/
│   ├── fixtures/                 trimmed real source files
│   └── test_*.py
├── docs/
│   ├── architecture.svg
│   ├── data_model.md
│   ├── data_licences.md
│   ├── privacy.md
│   ├── runbook.md
│   ├── sources/                  one file per source
│   └── decisions/                numbered decision records
└── data/                         git ignored: raw, bronze, warehouse
```


## 7. Environment setup (Windows, PowerShell)

Run each line in PowerShell from the folder where Paul keeps projects.

```powershell
# Install uv (skip if `uv` already runs)
irm https://astral.sh/uv/install.ps1 | iex

# Install Python 3.12 for this project
uv python install 3.12

# Create the project
mkdir sanctions-list-pipeline
cd sanctions-list-pipeline
git init
uv init
uv python pin 3.12

# Runtime dependencies
uv add duckdb dbt-core dbt-duckdb dagster dagster-webserver dagster-dbt httpx lxml selectolax rapidfuzz polars pyarrow "fastapi[standard]" pydantic jinja2 tenacity
```

Then add a development dependency group directly in `pyproject.toml` (uv installs this group by default on `uv sync`):

```toml
[dependency-groups]
dev = ["pytest", "ruff", "xmlschema", "respx"]

[tool.dagster]
module_name = "sanctions_platform.definitions"

[tool.ruff]
line-length = 100
```

Then run `uv sync`.

Windows notes for Claude Code:
* Use `Invoke-RestMethod` or `Invoke-WebRequest` for manual checks, not curl.
* Always use `pathlib` in Python. Never build paths with string concatenation.
* Open every text file with explicit UTF8 encoding.
* DuckDB allows one writer at a time. Stop the Dagster UI before running dbt by hand against the same database file, or point manual runs at a copy.


## 8. Build phases

Each phase ends with: all acceptance criteria proven, tests passing, a commit, and a Progress Log entry. Commit messages follow Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`, `chore:`).

### Phase 0. Bootstrap the repository
Tasks:
1. Run the setup in section 7.
2. Create the folder layout in section 6.
3. Write `.gitignore` covering `data/`, `.venv/`, `transform/target/`, `transform/logs/`, `transform/dbt_packages/`, `.dagster_home/`, `dashboard/dist/`, `__pycache__/`.
4. Write `docs/decisions/0001-stack.md` with the resolved versions and the reasons from section 5.
5. Paul creates an empty public repository named `sanctions-list-pipeline` on github.com under TechPaulFrey. Then:
   ```powershell
   git add .
   git commit -m "chore: bootstrap project structure"
   git branch -M main
   git remote add origin https://github.com/TechPaulFrey/sanctions-list-pipeline.git
   git push -u origin main
   ```
Acceptance criteria:
* `uv sync`, `uv run ruff check .` and `uv run pytest` all succeed (pytest may report zero tests).
* The repository is visible on GitHub with the layout above.

### Phase 1. Fetchers, raw store and manifest
Tasks:
1. `config.py`: hold the exact URLs from section 2, a User Agent string of `sanctions-list-pipeline/0.1 (+https://github.com/TechPaulFrey/sanctions-list-pipeline)`, a 60 second timeout, and the data paths.
2. Shared HTTP client: httpx with retries on connection errors and HTTP 429 and 5xx, using tenacity with exponential backoff (3 attempts, starting at 2 seconds). Send `If-None-Match` and `If-Modified-Since` when a previous ETag or Last-Modified value exists.
3. Raw store: write the file, then compute SHA256. If the hash matches the latest stored file for that source, delete the temporary file and record `unchanged` in the manifest.
4. Manifest table `raw_manifest` in DuckDB with columns: run_id, source, url, fetched_at_utc, http_status, etag, last_modified, bytes, sha256, outcome (`stored`, `unchanged`, `failed`), error_message, raw_path.
5. NIGSAC fetcher: first fetch https://nigsac.gov.ng/robots.txt and obey it. Fetch the list page, then each detail page, sleeping 2 seconds between requests. Store the list page and every detail page as raw HTML.
6. OFAC: also fetch the latest delta file and store it as its own source `ofac_delta`. Open it, document its real format in `docs/sources/ofac.md` before any code depends on it.
7. UK: fetch both XML and CSV.
8. Write `docs/sources/<source>.md` for all four sources: URL, format, observed size, update cadence, licence, quirks.
Acceptance criteria:
* One command fetches all sources: `uv run python -m sanctions_platform.fetch`.
* Running it twice in a row stores files on the first run and records `unchanged` for every source on the second.
* A simulated failure (unit test with respx returning HTTP 503) produces a `failed` manifest row and does not crash other sources.

### Phase 2. Parsers to bronze Parquet
Tasks:
1. Save trimmed real samples of each source into `tests/fixtures/` (for example the first 20 UN individuals and 10 entities, the first 30 SDN entries, the first 30 UK designations, and the full NIGSAC list page plus five detail pages). Keep the original structure; only remove records.
2. Write one parser per source producing Parquet in `data/bronze/<source>/<fetched_at_utc>.parquet`. Every row carries `raw_path`, `raw_sha256`, `fetched_at_utc`.
3. UN parser: individuals and entities, all name parts, aliases with quality labels, dates of birth (they come in several shapes: exact date, year only, ranges), nationalities, list type, reference number, listed on date.
4. OFAC parser: uid, type, names, aliases with weak or strong labels, programmes, identity documents, dates of birth, nationalities, and any UN reference found in remarks or identifiers.
5. UK parser: Unique ID, OFSI Group ID, UN reference number, regime, designation type, names and aliases, date designated, last updated. Validate each XML file against the XSD before parsing; a validation failure fails the asset.
6. NIGSAC parser: parse both tables and every detail page. Implement the reference number grammar from section 3 as a regular expression. Classify each row as individual, entity or group. Rows whose reference does not match go to a quarantine Parquet file with the reason.
7. Parse NIGSAC record dates as month first, store as naive local time plus a UTC column assuming West Africa Time (UTC+1), and convert `1/1/0001` to null with a flag.
Acceptance criteria:
* Unit tests for every parser run against fixtures with no network access.
* NIGSAC tests prove each issue in section 3 is handled: reused references keep both people, the null date becomes null with a flag, `NLIPBi.14-` is cleaned to `NLIPBi.14` with the raw value preserved, and the six groups are classified as groups.
* Row counts from the live parse are written to the manifest and match a manual count of the source for NIGSAC.

### Phase 3. dbt models and history
Tasks:
1. `transform/profiles.yml`:
   ```yaml
   sanctions_platform:
     target: dev
     outputs:
       dev:
         type: duckdb
         path: ../data/warehouse/sanctions.duckdb
         threads: 4
   ```
   Run dbt from inside `transform/` so this profile is picked up without extra arguments: `cd transform; uv run dbt build`.
2. Sources: declare bronze Parquet files as dbt sources with freshness thresholds (warn after 36 hours, error after 72 hours) based on `fetched_at_utc`.
3. Staging models, one per source, renaming to a shared vocabulary and casting types.
4. Intermediate model `int_parties_unified` with the columns in section 9.1.
5. Snapshot `parties_snapshot` using the check strategy on `record_hash`, giving valid_from and valid_to for every version of every party.
6. Marts:
   * `dim_party_current`: active parties today, one row per source and party.
   * `fct_list_changes`: one row per added, removed or modified party per day, with the changed fields listed.
   * `fct_cross_list_links`: produced in Phase 5.
   * `mart_source_freshness`: last successful fetch, last change, record count per source.
   * `mart_daily_summary`: counts by source, party type and change type, for the dashboard.
7. Seeds: `nigsac_reference_corrections.csv` (raw value, corrected value, evidence URL, date observed) and `name_token_equivalents.csv` (Phase 5).
8. Document every model and column in YAML. Generate docs with `uv run dbt docs generate`.
Acceptance criteria:
* `uv run dbt build` passes from a clean database.
* Running fetch, parse and dbt on two different days produces correct rows in `fct_list_changes`. Test this with two fixture snapshots that differ by known additions, removals and edits.

### Phase 4. Data quality
Tests to implement (dbt tests unless stated):
1. Not null and unique on every primary key. For NIGSAC the key is the detail page id, not the reference number.
2. Accepted values for party_type and source.
3. Volume anomaly: fail if any source's active record count drops by more than 10 percent day on day, warn above 2 percent. Rationale: a silent partial download looks like mass delistings.
4. Schema drift: a Python check that compares the set of XML element names and HTML table headers against the last accepted set and fails on any change.
5. UK format reconciliation: XML and CSV active record counts must match.
6. OFAC reconciliation: once the delta file format is documented, compare OFAC's reported additions and removals with ours for the same publication and fail on mismatch.
7. NIGSAC: every row either has a valid reference or sits in quarantine with a reason; a test fails if quarantine grows without a matching entry in the corrections seed.
8. Dates: no date of birth in the future, no listing date before 1999 for the UN list.
Acceptance criteria:
* Each test has a deliberately broken fixture that proves it fails.
* `docs/runbook.md` explains what to do when each test fails.

### Phase 5. Cross list matching
Tasks:
1. Deterministic links first: join on UN reference numbers wherever a party on the UK, OFAC or NIGSAC list carries one (the NIGSAC narratives cite UN references such as `QDe.138` for Boko Haram and `QDe.162` for ISWAP).
2. Name normalisation: case folding, diacritic removal, punctuation removal, whitespace collapse, token sorting, and replacement using `name_token_equivalents.csv`. Seed it only with variants observed in the data, such as MOHAMMED, MUHAMMAD, MUHAMMED, MOHAMMAD and ABDURRAHAMAN, ABDURRAHMAN, ABDULRAHMAN.
3. Blocking to keep comparisons small: compare only parties of the same type that share a normalised first token or a year of birth.
4. Scoring with rapidfuzz token set ratio on names and aliases, boosted by matching date of birth and nationality.
5. Evaluation: generate 150 candidate pairs across score bands. Paul labels each as match or not match in `analysis/labelled_pairs.csv`. Report precision and recall at three thresholds in `analysis/matching_evaluation.md`, and choose the threshold with a written reason.
Acceptance criteria:
* `fct_cross_list_links` holds link type (deterministic or fuzzy), score, and the evidence fields.
* The evaluation report exists with real numbers computed from Paul's labels.

### Phase 6. Orchestration with Dagster
Tasks:
1. Assets: one fetch asset per source, one parse asset per source, all dbt models loaded through the dbt integration, matching, dashboard export.
2. dbt tests appear as asset checks; failed blocking checks stop downstream assets.
3. Daily schedule at 06:00 UTC (07:00 in Lagos), after the UN's nightly regeneration.
4. Retry policy on fetch assets: 3 retries, 5 minutes apart.
5. Run locally with `uv run dagster dev` and open http://localhost:3000.
Acceptance criteria:
* A full materialisation succeeds from the UI.
* A screenshot of the asset graph is saved to `docs/images/asset_graph.png` for the README.

### Phase 7. Serving
API (`api/main.py`, run with `uv run fastapi dev api/main.py`):
* `GET /health`: status plus freshness per source.
* `GET /screen?name=<text>`: top 10 candidates across all lists with score, source, reference and link type. Name is required; empty input returns HTTP 422.
* `GET /parties/{party_key}`: current record and full history.
* `GET /changes?date=<YYYY-MM-DD>`: change events for that day.
* Tests with FastAPI's test client for every endpoint.

Dashboard (`dashboard/`):
* A Python script exports mart tables to JSON and renders static HTML with Jinja2 into `dashboard/dist/`.
* Pages: overview (records per source, last update per source), daily changes, cross list overlap, Nigeria focus (NIGSAC records and which also appear on UN, UK or OFAC lists).
* Must work on a phone screen.
* Follows the publishing rules in section 10.

Acceptance criteria:
* Every API endpoint has a passing test.
* The dashboard builds from a clean checkout plus one pipeline run.

### Phase 8. CI and the daily live run
1. `ci.yml` on every push and pull request: `uv sync`, `uv run ruff check .`, `uv run pytest`, then `dbt build` against fixture data only. CI never calls the live sources.
2. `daily.yml` on a schedule (`cron: "0 6 * * *"`) plus manual trigger: run the full pipeline against live sources, publish the dashboard to GitHub Pages.
3. History persistence between runs: the snapshot tables are exported as compressed Parquet to an orphan branch named `data-history` and restored at the start of each run. Raw files are uploaded as workflow artifacts kept for 30 days. Record this design and its trade offs in `docs/decisions/0003-history-persistence.md`.
4. Pin every third party action to its latest major version at build time and note the versions in the decision record.
Acceptance criteria:
* CI badge green on the README.
* Seven consecutive successful daily runs before the project is announced.

### Phase 9. Documentation and portfolio packaging
1. README sections: the problem, the four sources, architecture diagram, how to run locally on Windows, data quality approach, the NIGSAC findings from section 3, the UK OFSI migration, matching evaluation results, limitations, licence and privacy notes.
2. Every number in the README comes from a query in `analysis/readme_metrics.sql`, run on the date stated next to it. No estimated or rounded claims without a source query.
3. `docs/architecture.svg` drawn to match the real asset graph.
4. A 3 minute screen recording: run the pipeline, show a failed quality check, show the API and dashboard.
5. A project card for pauladebayo.com and an outline for a Medium article on what the Nigeria Sanctions List data quality issues mean for compliance teams.

### Phase 10. Extensions (only after Phase 9)
* OFAC advanced XML parser, compared field by field against SDN.XML.
* EU Consolidated Financial Sanctions List, after verifying URL and terms.
* Store history tables as Apache Iceberg with DuckDB.
* Email or Slack alert when a Nigeria related designation appears on any list.


## 9. Data model

### 9.1 `int_parties_unified`
* party_key: hash of source and source_id
* source: `un`, `ofac`, `uk`, `nigsac`
* source_id: UN reference, OFAC uid, UK Unique ID, NIGSAC detail page id
* source_reference: the reference as published (for NIGSAC the cleaned reference, with the raw value kept in source_reference_raw)
* legacy_id: OFSI Group ID for UK parties designated before 28 January 2026
* party_type: `individual`, `entity`, `group`, `vessel`, `aircraft`
* primary_name, primary_name_normalised
* aliases: list of name and quality label
* dates_of_birth: list, each with precision (`day`, `year`, `range`)
* nationalities: list of ISO 3166 alpha 2 codes where resolvable, raw text otherwise
* programmes_or_regimes: list
* un_reference: when the source cites one
* listed_on: date
* record_hash: hash of the canonical JSON of business fields only (never lineage fields)
* raw_path, raw_sha256, fetched_at_utc

### 9.2 `fct_list_changes`
change_date, source, party_key, change_type (`added`, `removed`, `modified`), changed_fields, previous_record_hash, new_record_hash.

### 9.3 `fct_cross_list_links`
link_id, party_key_a, party_key_b, link_type (`un_reference`, `fuzzy`), score, matched_on, created_at.


## 10. Privacy, licensing and publishing rules

1. NIGSAC detail pages include phone numbers, home addresses and passport numbers. The parser drops phone numbers and home addresses at staging. Passport numbers are kept only in the local warehouse for matching and are never shown in the API or the dashboard. Rationale and the relevant Nigeria Data Protection Act 2023 principles (data minimisation and purpose limitation) go in `docs/privacy.md`.
2. The NIGSAC site states all rights reserved. The public dashboard shows NIGSAC names, reference numbers and dates only, with a link to the official detail page. It never republishes narrative text. Raw NIGSAC files never enter the public repository. Paul may email info@nigsac.gov.ng to request permission for wider reuse; record any reply in `docs/data_licences.md`.
3. UK data: credit "Contains public sector information licensed under the Open Government Licence v3.0" on the dashboard.
4. UN and OFAC: record their terms of use in `docs/data_licences.md` during Phase 1, from the official sites.
5. The README and dashboard state clearly that this is a demonstration and must not be used for real screening decisions.


## 11. Working rules for Claude Code

1. Read this file at the start of every session. Work on one phase at a time, in order.
2. Never invent data, URLs, record counts, test results or metrics. If something cannot be verified, stop and write the question in the Progress Log for Paul.
3. Before naming anything user facing (project, dashboard title, package names beyond those defined here), ask Paul.
4. Give every command in PowerShell syntax.
5. Write tests alongside code, not after. A phase is not done while any test fails.
6. Small commits with clear messages. No commented out code, no unused files, no leftover debugging prints.
7. Comments explain why, not what. No filler text in code, docs or the README.
8. Record every non obvious decision as a numbered file in `docs/decisions/`.
9. Before a large or irreversible change (deleting data, rewriting history, changing the data model), describe the change and wait for Paul's approval.
10. End every session by appending a dated Progress Log entry: what was done, what was proven, what is blocked, and the exact next step.


## 12. Risks and mitigations

1. NIGSAC changes its page layout. Mitigation: schema drift check fails fast; raw HTML is kept so the parser can be fixed and history replayed.
2. NIGSAC site is slow or unreachable. Mitigation: retries, then a `failed` manifest row; freshness warnings appear on the dashboard rather than a crash.
3. OFAC file size makes CI slow. Mitigation: CI uses fixtures only; the live run is the daily workflow.
4. Matching false positives with common names (for example many variants of Muhammad). Mitigation: blocking on date of birth and type, measured precision, and the demonstration disclaimer.
5. GitHub Actions schedules can be delayed or disabled after 60 days without repository activity. Mitigation: freshness checks show the gap; the runbook explains how to re enable.
6. Scope creep. Mitigation: Phase 10 items stay frozen until Phase 9 is complete.


## 13. Definition of done

* All four sources ingested daily, with seven consecutive successful scheduled runs.
* Every acceptance criterion in Phases 0 to 9 proven and ticked.
* CI green, test suite covering fetchers, parsers, dbt models, matching and API.
* Public dashboard live on GitHub Pages; API demonstrated in the recording.
* README complete, every number traceable to a query.
* Paul can explain every design decision from the decision records.


## 14. References

* UN Security Council Consolidated List: https://www.un.org/securitycouncil/content/un-sc-consolidated-list
* OFAC Sanctions List Service: https://sanctionslist.ofac.treas.gov/Home/static/index.html
* OFAC FAQ on the advanced sanctions list standard: https://ofac.treasury.gov/sdn-list-data-formats-data-schemas/frequently-asked-questions-on-advanced-sanctions-list-standard
* The UK Sanctions List: https://www.gov.uk/government/publications/the-uk-sanctions-list
* Moving to a single list for UK sanctions designations: https://www.gov.uk/guidance/moving-to-a-single-list-for-uk-sanctions-designations-28-january-2026
* Nigeria Sanctions List: https://nigsac.gov.ng/IndSancList
* Voice of Nigeria report on the June 2026 designations: https://von.gov.ng/nigeria-welcomes-u-s-sanctions-on-alleged-terrorism-financiers/
* OpenSanctions licensing (reason for exclusion): https://www.opensanctions.org/docs/commercial/exemption/


## 15. Progress Log

### 26 October 2026, planning session (Claude in claude.ai)
Done:
* Selected the project from five ranked candidates.
* Verified live URLs and formats for the UN, OFAC, UK and NIGSAC sources.
* Confirmed NIGSAC publishes HTML only, with 54 individual and group rows and 15 entity rows; latest record date 18 June 2026.
* Recorded 13 NIGSAC data quality issues from the live page (section 3).
* Confirmed the OFSI Consolidated List closure on 28 January 2026 and the UK Unique ID migration.
Blocked or open:
* Paul to confirm the final project name (working title in use).
* EU list URL and terms not yet verified (Phase 10).
* OFAC delta file format to be documented in Phase 1.
Next step:
* Claude Code starts Phase 0, section 7, in Paul's projects folder.

### 26 October 2026, Phase 0 session (Claude Code)
Done:
* Created the project at `C:\Users\paulf\global-sanctions-data-platform` with git, uv and Python 3.12.13.
* `uv init` defaulted to `requires-python >= 3.13`; corrected to `>=3.12,<3.13` and pinned `.python-version` to 3.12.
* Switched from the flat `uv init` app layout to a `src/sanctions_platform` package built with hatchling, so the package imports cleanly in tests and Dagster. Removed the generated `main.py`.
* Installed all runtime and dev dependencies; `uv.lock` generated. Resolved versions recorded in `docs/decisions/0001-stack.md`.
* Created the section 6 folder layout. Empty folders hold a `.gitkeep` so the layout is visible on GitHub; each is removed when the folder gets real content.
* Wrote `.gitignore`, a README stub with the demonstration disclaimer, and `tests/test_package.py` (import smoke test; pytest exits non-zero when it collects zero tests).
* Paul chose the project name Sanctions List Pipeline (repo `sanctions-list-pipeline`). Replaced the working title in every file (`pyproject.toml`, `README.md`, this log, `uv.lock` regenerated) The local folder rename was blocked because Windows reported it in use; Paul to rename it to `sanctions-list-pipeline` after closing it in VS Code. The Python package name `sanctions_platform` is unchanged, as defined in section 6.
Proven:
* `uv sync` succeeds, `uv run ruff check .` reports all checks passed, `uv run pytest` reports 1 passed.
* Pushed to https://github.com/TechPaulFrey/sanctions-list-pipeline; remote `main` matches local HEAD. Paul's repo had a GitHub-generated README commit, merged with `--allow-unrelated-histories` (project README kept), no force push.
* Paul made the repo public. The unauthenticated GitHub API reports `visibility: public` and lists the section 6 layout at the repo root.
* Phase 0 acceptance criteria: both met.
Blocked or open:
* Paul to rename the local folder to `sanctions-list-pipeline` (blocked while open in VS Code).
Next step:
* After the push, start Phase 1, task 1 (`config.py`), re-verifying each source URL first.

### 26 October 2026, Phase 1 session (Claude Code)
Done:
* Re-verified every source URL live (results in `docs/sources/`). All returned HTTP 200. NIGSAC robots.txt returns 404, meaning no restrictions.
* Found the SDN.XML URL: https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.XML. The OFAC page builds its links in JavaScript; this URL follows the documented advanced-file pattern.
* Built `config.py`, the httpx client with tenacity retries (3 attempts, 2 s then 4 s, on connection errors, 429 and 5xx) and conditional requests, the raw store, the `raw_manifest` table, the NIGSAC crawler (robots.txt, 2 s delay) and the CLI `uv run python -m sanctions_platform.fetch` (exits 1 if any source failed).
* Documented the OFAC delta format: DeltaFile 1.0 XML with `entity/@action`. The delta entity id equals the SDN.XML uid, verified on the 21 October 2026 file (18 adds all present in SDN.XML, 4 removes all absent).
* The NIGSAC list page embeds the server clock, so it was re-stored on every run. Added `content_sha256` to the manifest; raw bytes stay unaltered. Decision 0002. Phase 8's history persistence record renumbered to 0003.
* Wrote the four source docs and `docs/data_licences.md`.
Proven:
* 14 tests pass offline (13 fetch tests with respx, 1 package test), including HTTP 503 giving a `failed` row (3 attempts) while other sources store, 304 handling, robots.txt disallow, and clock-only changes on the list page.
* Live: the first run stored every source (UN 1, OFAC 1, delta 1, UK XML 1, UK CSV 1, NIGSAC list 1, NIGSAC detail 69). After the clock fix, two consecutive runs: the second recorded `unchanged` for every source. UN, OFAC and UK answered 304; NIGSAC compared hashes.
* UK XML and CSV hold the same 6,423 Unique IDs. The CSV has one row per name, so Phase 4 must reconcile distinct IDs, not rows.
* All Phase 1 acceptance criteria met.
Findings for later phases:
* The UN file was last generated 24 October 23:00 UTC and was still current on 26 October 14:27 UTC, so "nightly" did not hold over this weekend. Watch before fixing the 36-hour freshness threshold.
* NIGSAC entity detail pages do carry a reference number (label misspelled "Referance Number"), refining section 3 issue 9.
* NIGSAC tab clock reads Lagos time, which supports the UTC+1 assumption in Phase 2.
Blocked or open:
* UN terms: only the general UN website terms were found, which allow personal, non-commercial use with no redistribution. Paul to resolve before publishing the dashboard (details in `docs/data_licences.md`).
* OFAC terms: no statement found. Paul to confirm.
* Local folder rename to `sanctions-list-pipeline` still pending.
* Paul asked to remove Claude as a contributor. Future commits carry no Co-Authored-By trailer. Removing it from already pushed commits needs a history rewrite and force push; waiting for Paul's approval (rule 9).
Next step:
* Phase 2, task 1: save trimmed fixtures from today's raw files into `tests/fixtures/`, keeping NIGSAC personal data out of the public repo.
