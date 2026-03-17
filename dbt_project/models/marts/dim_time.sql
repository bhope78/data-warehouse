-- Dimension: Time
-- Date spine covering the analysis period

with date_spine as (
    {{ dbt_utils.date_spine(
        datepart="month",
        start_date="cast('2018-01-01' as date)",
        end_date="cast('2026-12-01' as date)"
    ) }}
)

select
    date_month as date_id,
    extract(year from date_month) as year,
    extract(quarter from date_month) as quarter,
    extract(month from date_month) as month,
    to_char(date_month, 'Month') as month_name
from date_spine
