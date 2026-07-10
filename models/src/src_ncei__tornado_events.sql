select
  cast(event_id as varchar) as event_id,
  upper(state) as state,
  county,
  occurred_at,
  begin_location,
  end_location,
  upper(tor_f_scale) as rating_code,
  try_cast(tor_length as double) as path_length_miles,
  try_cast(tor_width as integer) as path_width_yards,
  try_cast(begin_lat as double) as begin_latitude,
  try_cast(begin_lon as double) as begin_longitude,
  try_cast(end_lat as double) as end_latitude,
  try_cast(end_lon as double) as end_longitude,
  coalesce(try_cast(injuries_direct as integer), 0) as injuries,
  coalesce(try_cast(deaths_direct as integer), 0) as fatalities,
  property_damage_usd,
  crop_damage_usd,
  event_narrative,
  source_url
from {{ source('raw', 'ncei_tornado_events') }}
where event_type = 'Tornado'
