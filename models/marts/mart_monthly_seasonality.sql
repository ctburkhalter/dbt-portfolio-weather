with regions as (
  select 'alabama' as region, * from {{ ref('fct_tornado_events') }} where is_alabama
  union all
  select 'dixie' as region, * from {{ ref('fct_tornado_events') }} where is_dixie_cohort
  union all
  select 'tornado' as region, * from {{ ref('fct_tornado_events') }} where is_tornado_cohort
)
select
  region,
  extract(month from occurred_at)::integer as month_number,
  strftime(occurred_at, '%b') as month,
  count(*) as tornadoes,
  count(*) filter (where rating_value >= 2) as significant_tornadoes
from regions
group by 1, 2, 3
