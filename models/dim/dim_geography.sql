with locations as (
  select distinct state, county
  from {{ ref('src_ncei__tornado_events') }}
)
select
  state,
  county,
  case when state = 'AL' then true else false end as is_alabama,
  case when state in ('AL', 'AR', 'GA', 'LA', 'MS', 'TN') then true else false end as is_dixie_cohort,
  case when state in ('CO', 'IA', 'KS', 'NE', 'OK', 'SD', 'TX') then true else false end as is_tornado_cohort
from locations
