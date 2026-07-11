with regions as (
    select 'alabama' as region, occurred_at, rating_value, record_status
    from {{ ref('fct_tornado_events') }}
    where is_alabama
    union all
    select 'dixie' as region, occurred_at, rating_value, record_status
    from {{ ref('fct_tornado_events') }}
    where is_dixie_cohort
    union all
    select 'tornado' as region, occurred_at, rating_value, record_status
    from {{ ref('fct_tornado_events') }}
    where is_tornado_cohort
)
select
    region, extract(month from occurred_at)::integer as month_number,
    strftime(occurred_at, '%b') as month,
    count(*) filter (where record_status = 'confirmed') as confirmed_tornadoes,
    count(*) filter (where record_status = 'preliminary') as preliminary_tornado_reports,
    count(*) filter (where record_status = 'confirmed' and rating_value >= 2) as significant_tornadoes
from regions
group by 1, 2, 3
order by 1, 2
