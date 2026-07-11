select
    extract(year from occurred_at)::integer as year,
    count(*) filter (where record_status = 'confirmed') as confirmed_tornadoes,
    count(*) filter (where record_status = 'preliminary') as preliminary_tornado_reports,
    count(*) filter (where record_status = 'confirmed' and rating_value >= 2) as significant_tornadoes
from {{ ref('fct_tornado_events') }}
where is_alabama
group by 1
order by 1
