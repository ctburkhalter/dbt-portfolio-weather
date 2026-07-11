select
  cast(event_id as varchar) as event_id,
  upper(state) as state,
  county,
  -- occurred_at (raw) is a full ISO-8601 string with an explicit UTC offset,
  -- for example "2020-01-01T14:30:00-06:00" (see load_ncei_events.parse_timestamp).
  -- Strip the offset to recover NCEI's local wall-clock reading unshifted;
  -- casting the full string (offset included) to TIMESTAMP instead normalizes
  -- deterministically to a UTC-equivalent naive value for cross-source comparison.
  cast(regexp_replace(occurred_at, '[+-][0-9]{2}:[0-9]{2}$', '') as timestamp) as occurred_at,
  cast(occurred_at as timestamp) as occurred_at_utc,
  regexp_extract(occurred_at, '([+-][0-9]{2}:[0-9]{2})$', 1) as occurred_at_utc_offset,
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
