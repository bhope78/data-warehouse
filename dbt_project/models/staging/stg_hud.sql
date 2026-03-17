-- Staging: HUD fair market rent data

with source as (
    select * from {{ source('raw', 'hud_rents') }}
)

select
    -- TODO: Map raw HUD columns once ingestion is implemented
    *
from source
