select
    state, county,
    count(*) filter (where record_status = 'confirmed') as confirmed_tornadoes,
    count(*) filter (where record_status = 'preliminary') as preliminary_tornado_reports,
    count(*) filter (where record_status = 'confirmed' and rating_value >= 2) as significant_tornadoes,
    sum(injuries) filter (where record_status = 'confirmed') as injuries,
    max_by(rating_code, rating_value) filter (where record_status = 'confirmed') as max_rating
from {{ ref('fct_tornado_events') }}
where is_alabama
group by state, county
order by confirmed_tornadoes desc, state asc, county asc
