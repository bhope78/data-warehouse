# Relocation Data Warehouse

An end-to-end data pipeline and analytics platform to identify the best US cities to relocate to — based on cost of living, housing affordability, job availability, income, and crime statistics.

## Architecture

```
[5 Public APIs] → [Python Ingestion] → [AWS Redshift / Postgres]
                                              ↓
                                    [dbt Transformations]
                                              ↓
                                    [Star Schema (Facts + Dims)]
                                              ↓
                          [Apache Superset + Folium Maps + Flask Site]
```

## Tech Stack

| Layer | Tool |
|---|---|
| Ingestion | Python (requests, pandas) |
| Warehouse | AWS Redshift (Postgres for local dev) |
| Modeling | dbt (star schema) |
| Visualization | Apache Superset |
| Maps | Folium (choropleth) |
| Charts | Chart.js |
| Frontend | Flask |

## Data Sources

| Source | Data | API |
|---|---|---|
| Bureau of Labor Statistics | Wages, employment, unemployment | [BLS API](https://www.bls.gov/bls/api_features.htm) |
| US Census Bureau | Income, housing, demographics | [Census API](https://www.census.gov/data/developers/data-sets.html) |
| HUD | Fair market rents, affordability | [HUD API](https://www.hud.gov/program_offices/comm_planning/affordablehousing) |
| FBI Crime Data | Crime rates by city/region | [FBI API](https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/docApi) |
| Numbeo | Cost of living indexes | [Numbeo API](https://www.numbeo.com/common/api.jsp) |

## Data Model

**Star schema** with geography as the central dimension:

- `dim_geography` — cities, counties, states (FIPS codes, coordinates)
- `dim_time` — date spine (year, quarter, month)
- `fct_economics` — wages, employment, unemployment
- `fct_housing` — rents, home values, affordability
- `fct_crime` — crime rates per 100k
- `fct_quality_of_life` — cost of living, composite scores

## Quick Start

```bash
# Clone and setup
git clone https://github.com/bhope78/data-warehouse.git
cd data-warehouse
make setup

# Start local Postgres + Superset
make up

# Run ingestion (once implemented)
make ingest

# Run dbt models
make dbt-run
make dbt-test

# Full pipeline refresh
make refresh
```

## Project Structure

```
├── ingestion/          # Python scripts for each API data source
├── dbt_project/        # dbt models, seeds, tests, macros
├── frontend/           # Flask app with Folium maps
├── docker/             # Docker Compose (Postgres, Superset)
├── infrastructure/     # AWS Redshift provisioning
├── scripts/            # Pipeline orchestration
└── notebooks/          # Exploratory analysis
```

## Key Questions Answered

1. Which cities have the best salary-to-cost-of-living ratio for software engineers?
2. Where is housing most affordable relative to local income?
3. Which metros have low crime AND high job availability?
4. How have housing prices changed year over year by region?

## License

MIT
