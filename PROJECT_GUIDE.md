# Relocation Data Warehouse — Project Guide

## Goal
Build an end-to-end data pipeline and analytics dashboard to identify the best US cities to relocate to based on cost of living, housing affordability, job availability, income, and crime.

## Tech Stack
| Layer | Tool |
|---|---|
| Data ingestion | Python |
| Cloud data warehouse | AWS Redshift |
| Local dev database | PostgreSQL 15 (Redshift-compatible) |
| Data modeling | dbt (star schema) |
| Visualization | Apache Superset (self-hosted) |
| Mapping / GIS | Folium |
| Charts | Chart.js |
| Frontend | Flask |
| Version control | Git / GitHub |

**Key decisions:**
- Flask over Next.js — keeps the entire stack in Python
- Postgres as local Redshift stand-in — Redshift is Postgres-compatible at the SQL level
- dbt profiles use `target` toggle: `dev` (Postgres) vs `prod` (Redshift)
- Monorepo — everything in one Git repo

---

## Architecture
```
[APIs] → [Python ingestion scripts] → [Postgres/Redshift (raw schema)]
                                              ↓
                                    [dbt transformations]
                                              ↓
                               [staging schema → marts schema (star schema)]
                                              ↓
                          [Apache Superset dashboards + Folium maps]
                                              ↓
                              [Flask website with explanatory content]
```

---

## Directory Structure
```
data-warehouse/
├── .github/workflows/ci.yml
├── docker/
│   ├── docker-compose.yml
│   ├── superset/
│   │   ├── Dockerfile
│   │   └── superset_config.py
│   └── postgres/
│       └── init.sql                  # Creates raw, staging, marts schemas
├── ingestion/
│   ├── __init__.py
│   ├── base.py                       # Abstract base class for all ingestors
│   ├── bls.py                        # Bureau of Labor Statistics
│   ├── census.py                     # Census Bureau
│   ├── hud.py                        # HUD
│   ├── fbi_crime.py                  # FBI Crime Data
│   ├── numbeo.py                     # Numbeo
│   ├── utils.py                      # Shared helpers (retry, rate-limit, logging)
│   └── tests/
│       ├── __init__.py
│       ├── test_bls.py
│       ├── test_census.py
│       ├── test_hud.py
│       ├── test_fbi_crime.py
│       └── test_numbeo.py
├── dbt_project/
│   ├── dbt_project.yml
│   ├── packages.yml
│   ├── profiles.yml                  # NOT committed — in .gitignore
│   ├── models/
│   │   ├── staging/
│   │   │   ├── _staging__models.yml  # Source definitions + tests
│   │   │   ├── stg_bls.sql
│   │   │   ├── stg_census.sql
│   │   │   ├── stg_hud.sql
│   │   │   ├── stg_fbi_crime.sql
│   │   │   └── stg_numbeo.sql
│   │   └── marts/
│   │       ├── _marts__models.yml
│   │       ├── dim_geography.sql     # FIPS, city, state, lat/lng, metro
│   │       ├── dim_time.sql          # Date spine
│   │       ├── fct_economics.sql     # BLS + Census wages/employment
│   │       ├── fct_housing.sql       # HUD rents/affordability
│   │       ├── fct_crime.sql         # FBI crime stats
│   │       └── fct_quality_of_life.sql
│   ├── seeds/
│   │   ├── state_fips_codes.csv
│   │   └── county_fips_codes.csv
│   ├── tests/
│   │   └── assert_positive_population.sql
│   ├── macros/
│   │   └── generate_schema_name.sql
│   └── snapshots/
│       └── .gitkeep
├── frontend/
│   ├── app.py                        # Flask entry point
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html
│   │   └── map.html
│   ├── static/
│   │   ├── css/style.css
│   │   └── js/charts.js
│   └── maps/
│       └── map_builder.py            # Folium map generation
├── infrastructure/
│   ├── redshift/
│   │   ├── create_cluster.py         # Boto3 Redshift provisioning
│   │   ├── create_schemas.sql
│   │   └── iam_policy.json
│   └── superset/
│       └── setup_dashboards.py
├── scripts/
│   ├── run_ingestion.py              # Orchestrator
│   ├── full_refresh.sh               # Ingest + dbt run + dbt test
│   └── setup_local.sh               # One-command local setup
├── notebooks/
│   └── exploration.ipynb
├── .env.example
├── .gitignore
├── .python-version
├── Makefile
├── pyproject.toml
├── requirements.txt
└── PROJECT_GUIDE.md                  # This file
```

---

## Data Sources

### 1. Bureau of Labor Statistics (BLS)
- **Data:** Wages/employment by occupation and metro, unemployment rates
- **API docs:** https://www.bls.gov/bls/api_features.htm
- **Update frequency:** Annual (May release)
- **Auth:** API key (free registration)

### 2. US Census Bureau
- **Data:** Median home values, rents, income, demographics, commute times
- **API docs:** https://www.census.gov/data/developers/data-sets.html
- **Update frequency:** Annual (American Community Survey)
- **Auth:** API key (free)

### 3. HUD (Housing and Urban Development)
- **Data:** Fair market rents, housing affordability, building permits
- **API docs:** https://www.hud.gov/program_offices/comm_planning/affordablehousing
- **Update frequency:** Annual
- **Auth:** API token (free)

### 4. FBI Crime Data Explorer
- **Data:** Crime statistics by city/region
- **API docs:** https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/docApi
- **Update frequency:** Regular
- **Auth:** API key (free)
- **Note:** UCR/NIBRS transition means data format varies by year

### 5. Numbeo
- **Data:** Cost of living indexes, quality of life scores
- **API docs:** https://www.numbeo.com/common/api.jsp
- **Update frequency:** Regularly (crowdsourced)
- **Auth:** API key (free tier available, may need paid for full access)

---

## Data Model — Star Schema

### Fact Tables
| Table | Source | Key Metrics |
|---|---|---|
| `fct_economics` | BLS + Census | median_wage, unemployment_rate, job_count |
| `fct_housing` | HUD + Census | median_rent, median_home_value, affordability_ratio |
| `fct_crime` | FBI | crime_rate_per_100k, violent_crime_rate, property_crime_rate |
| `fct_quality_of_life` | Numbeo | cost_of_living_index, quality_of_life_score, value_score |

### Dimension Tables
| Table | Description |
|---|---|
| `dim_geography` | city_id, city_name, county, state, FIPS, lat, lng, metro_area, region |
| `dim_time` | date_id, year, quarter, month (date spine) |

**Join key:** All facts join to `dim_geography` via FIPS code or city_id. This is the linchpin of the schema — different sources use different geo identifiers (FIPS, city names, ZIP, MSA codes), so staging models must standardize to a common key.

---

## Key Analytical Questions
1. Which cities have the best salary-to-cost-of-living ratio for software engineers?
2. Where is housing most affordable relative to local income?
3. Which metros have low crime AND high job availability?
4. How have housing prices changed year over year by region?

---

## Ingestion Pattern

Each data source extends `BaseIngestor`:

```python
class BaseIngestor(ABC):
    def __init__(self, source_name: str):
        self.source_name = source_name
        self.conn = self._get_connection()

    @abstractmethod
    def extract(self) -> pd.DataFrame: ...

    def load(self, df: pd.DataFrame, table_name: str): ...

    def run(self):
        df = self.extract()
        self.load(df, f"raw.{self.source_name}")
```

---

## Environment Variables (.env)
```
# Database (local Postgres / prod Redshift)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=data_warehouse
DB_USER=postgres
DB_PASSWORD=postgres
DB_SCHEMA=raw

# AWS (production)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-west-2
REDSHIFT_WORKGROUP=
REDSHIFT_DATABASE=

# API Keys
BLS_API_KEY=
CENSUS_API_KEY=
HUD_API_TOKEN=
FBI_API_KEY=
NUMBEO_API_KEY=

# Superset
SUPERSET_SECRET_KEY=
SUPERSET_ADMIN_PASSWORD=admin
```

---

## Makefile Commands
| Command | Description |
|---|---|
| `make setup` | First-time local setup (copy .env, install deps, start Docker) |
| `make up` | Start Postgres + Superset containers |
| `make down` | Stop containers |
| `make ingest` | Run all ingestion scripts |
| `make ingest-bls` | Run single ingestor |
| `make dbt-run` | Run dbt models |
| `make dbt-test` | Run dbt tests |
| `make lint` | Lint Python with ruff |
| `make test` | Run pytest |
| `make refresh` | Full pipeline: ingest → dbt run → dbt test |

---

## Implementation Phases

### Phase 1: Foundation
- [x] Create directory structure
- [ ] Write `.env.example`, `pyproject.toml`, `requirements.txt`, `Makefile`, `.gitignore`
- [ ] Write `docker-compose.yml` with Postgres + Superset
- [ ] Write `init.sql` (raw, staging, marts schemas)
- [ ] Init git repo, push to GitHub
- [ ] Verify `make setup` and `make up` work

### Phase 2: First Two Ingestors
- [ ] Implement `base.py` abstract ingestor
- [ ] Implement `bls.py` — register for API key, pull wage/employment data
- [ ] Implement `census.py` — register for API key, pull ACS data
- [ ] Verify data lands in `raw` schema in local Postgres

### Phase 3: dbt Models
- [ ] Init dbt project (`dbt init`)
- [ ] Seed FIPS lookup CSVs
- [ ] Build staging models (clean/rename columns from raw)
- [ ] Build `dim_geography` and `dim_time`
- [ ] Build `fct_economics` and `fct_housing`
- [ ] Add schema tests (not_null, unique, relationships)

### Phase 4: Remaining Sources
- [ ] Implement `hud.py`, `fbi_crime.py`, `numbeo.py`
- [ ] Build corresponding staging + fact models
- [ ] Add tests

### Phase 5: Frontend + Visualization
- [ ] Flask app with landing page
- [ ] Folium choropleth maps (salary-to-COL, crime, affordability)
- [ ] Connect Superset to Postgres, build dashboards
- [ ] Chart.js for interactive charts on Flask pages

### Phase 6: Production
- [ ] Provision Redshift Serverless via Boto3
- [ ] Configure IAM policies
- [ ] Switch dbt target to `prod`
- [ ] Deploy Flask app + Superset to EC2 or ECS
- [ ] Set up scheduled ingestion (cron or Airflow)

---

## Known Challenges
- **Numbeo:** May not have a truly free API — plan for scraping fallback or paid tier
- **FBI Crime:** UCR/NIBRS transition causes schema differences across years
- **Geography joining:** Sources use different identifiers (FIPS, city names, ZIP, MSA). The `dim_geography` dimension needs crosswalk logic using Census FIPS lookup seeds
- **Redshift vs Postgres:** Minor SQL differences (`DISTKEY`/`SORTKEY` are Redshift-only). Use dbt `config` blocks per-target
