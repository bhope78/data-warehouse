-- Staging: Census ACS data
-- Cleans raw Census data, extracts income/housing/demographic fields

with source as (
    select * from {{ source('raw', 'census_acs') }}
)

select
    -- TODO: Map raw Census columns once ingestion is implemented
    *
from source
