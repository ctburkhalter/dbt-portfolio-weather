with annual as (
  select *
  from {{ ref('mart_annual_trend_current') }}
),

confirmed as (
  select
    extract(year from occurred_at)::integer as year,
    count(*) as confirmed_tornadoes
  from {{ ref('fct_tornado_events_current') }}
  where is_alabama
    and record_status = 'confirmed'
  group by 1
)

select annual.*
from annual
left join confirmed using (year)
where annual.tornadoes != coalesce(confirmed.confirmed_tornadoes, 0)
