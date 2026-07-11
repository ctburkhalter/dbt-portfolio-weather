with cutoff as (
  select max(occurred_at_utc) as confirmed_through
  from {{ ref('fct_tornado_events') }} where record_status = 'confirmed'
)
select event.* from {{ ref('fct_tornado_events') }} as event cross join cutoff
where event.record_status = 'preliminary' and event.occurred_at_utc <= cutoff.confirmed_through
