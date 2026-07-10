select
  extract(year from occurred_at)::integer as year,
  count(*) as tornadoes,
  count(*) filter (where rating_value >= 2) as significant_tornadoes
from {{ ref('fct_tornado_events') }}
where is_alabama
group by 1
order by 1
