select
  event.event_id,
  event.occurred_at,
  event.state,
  event.county,
  event.begin_location,
  event.end_location,
  intensity.rating_code,
  intensity.scale_system,
  intensity.rating_value,
  intensity.intensity_class,
  intensity.wind_estimate_low_mph,
  intensity.wind_estimate_high_mph,
  intensity.wind_estimate_note,
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
  event.event_narrative as narrative,
  event.source_url,
  geography.is_alabama,
  geography.is_dixie_cohort,
  geography.is_tornado_cohort
from {{ ref('src_ncei__tornado_events') }} as event
left join {{ ref('dim_tornado_intensity') }} as intensity
  on case
    when regexp_matches(trim(event.rating_code), '^EF[0-5]$') then trim(event.rating_code)
    when regexp_matches(trim(event.rating_code), '^F[0-5]$') then trim(event.rating_code)
    else 'Unknown'
  end = intensity.rating_code
left join {{ ref('dim_geography') }} as geography using (state, county)
