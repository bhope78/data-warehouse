-- Staging: FBI crime data
-- Normalizes across UCR/NIBRS reporting formats

with source as (
    select * from {{ source('raw', 'fbi_crime') }}
)

select
    -- TODO: Map raw FBI columns once ingestion is implemented
    *
from source
