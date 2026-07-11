with locations as (
  select distinct state, county
  from {{ ref('src_ncei__tornado_events') }}
)
select
  state,
  county,
  {{ cohort_flags('state') }}
from locations
