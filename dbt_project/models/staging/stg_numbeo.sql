-- Staging: Numbeo cost of living and quality of life data

with source as (
    select * from {{ source('raw', 'numbeo_col') }}
)

select
    -- TODO: Map raw Numbeo columns once ingestion is implemented
    *
from source
