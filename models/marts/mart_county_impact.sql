select
  county,
  count(*) as tornadoes,
  count(*) filter (where rating_value >= 2) as significant_tornadoes,
  sum(injuries) as injuries,
  max_by(rating_code, rating_value) as max_rating
from {{ ref('fct_tornado_events') }}
where is_alabama
group by 1
order by tornadoes desc, county
