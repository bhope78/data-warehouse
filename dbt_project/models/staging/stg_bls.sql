-- Staging: BLS wage and employment data
-- Cleans raw BLS data, standardizes column names

with source as (
    select * from {{ source('raw', 'bls_wages') }}
)

select
    -- TODO: Map raw BLS columns once ingestion is implemented
    *
from source
