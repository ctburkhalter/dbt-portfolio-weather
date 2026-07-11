with expected as (
  select extract(year from occurred_at)::integer as year,
    count(*) filter (where record_status = 'confirmed') as confirmed_tornadoes,
    count(*) filter (where record_status = 'preliminary') as preliminary_tornado_reports,
    count(*) filter (where record_status = 'confirmed' and rating_value >= 2) as significant_tornadoes
  from {{ ref('fct_tornado_events') }} where is_alabama group by 1
)
select actual.* from {{ ref('agg_tornado_events__annual') }} actual
full join expected using (year)
where actual.confirmed_tornadoes != expected.confirmed_tornadoes
  or actual.preliminary_tornado_reports != expected.preliminary_tornado_reports
  or actual.significant_tornadoes != expected.significant_tornadoes
  or actual.year is null or expected.year is null
