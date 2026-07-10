select distinct
  cast(occurred_at as date) as date_day,
  extract(year from occurred_at)::integer as year,
  extract(month from occurred_at)::integer as month_number,
  monthname(occurred_at) as month_name
from {{ ref('src_ncei__tornado_events') }}
where occurred_at is not null
