-- Dimension: Geography
-- Central dimension joining all fact tables via FIPS code
-- Seeded from FIPS CSVs, enriched with Census data

with fips as (
    select
        state_fips || county_fips as geo_id,
        county_name,
        state_name,
        state_abbr,
        state_fips,
        county_fips
    from {{ ref('county_fips_codes') }}
)

select
    geo_id,
    county_name,
    state_name,
    state_abbr,
    state_fips,
    county_fips
    -- TODO: Add lat/lng, metro_area, region from Census data
from fips
