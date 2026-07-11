with confirmed_cutoff as (
  -- occurred_at_utc is a UTC-equivalent naive timestamp for every source (see
  -- src_ncei__tornado_events and src_iem__preliminary_tornado_reports), so
  -- this cutoff compares absolute instants rather than mixing NCEI's local
  -- wall-clock time against IEM's UTC wall-clock time as raw strings.
  select max(occurred_at_utc) as max_confirmed_occurred_at_utc
  from {{ ref('fct_tornado_events') }}
),

confirmed as (
  select
    event_id,
    occurred_at,
    occurred_at_utc,
    occurred_at_utc_offset,
    state,
    county,
    begin_location,
    end_location,
    rating_code,
    scale_system,
    rating_value,
    intensity_class,
    wind_estimate_low_mph,
    wind_estimate_high_mph,
    wind_estimate_note,
    path_length_miles,
    path_width_yards,
    begin_latitude,
    begin_longitude,
    end_latitude,
    end_longitude,
    injuries,
    fatalities,
    property_damage_usd,
    crop_damage_usd,
    narrative,
    source_url,
    is_alabama,
    is_dixie_cohort,
    is_tornado_cohort,
    cast(null as varchar) as source_attribution,
    cast(null as varchar) as wfo,
    'confirmed' as record_status,
    'ncei_storm_events' as source_system,
    false as is_surveyed_track
  from {{ ref('fct_tornado_events') }}
),

preliminary as (
  select
    event.event_id,
    event.occurred_at,
    event.occurred_at_utc,
    event.occurred_at_utc_offset,
    event.state,
    event.county,
    event.begin_location,
    event.end_location,
    event.rating_code,
    event.scale_system,
    event.rating_value,
    event.intensity_class,
    event.wind_estimate_low_mph,
    event.wind_estimate_high_mph,
    event.wind_estimate_note,
    event.path_length_miles,
    event.path_width_yards,
    event.begin_latitude,
    event.begin_longitude,
    event.end_latitude,
    event.end_longitude,
    event.injuries,
    event.fatalities,
    event.property_damage_usd,
    event.crop_damage_usd,
    event.narrative,
    event.source_url,
    event.is_alabama,
    event.is_dixie_cohort,
    event.is_tornado_cohort,
    event.report_source as source_attribution,
    event.wfo,
    'preliminary' as record_status,
    'iem_lsr' as source_system,
    false as is_surveyed_track
  from {{ ref('fct_preliminary_tornado_reports') }} as event
  cross join confirmed_cutoff
  where event.occurred_at_utc > confirmed_cutoff.max_confirmed_occurred_at_utc
)

select * from confirmed
union all
select * from preliminary
