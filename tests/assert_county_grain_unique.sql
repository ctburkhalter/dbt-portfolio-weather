select state, county, count(*) as row_count
from {{ ref('agg_tornado_events__county') }}
group by 1, 2
having count(*) > 1
