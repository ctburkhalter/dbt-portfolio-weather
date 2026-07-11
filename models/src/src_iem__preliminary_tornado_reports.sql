select
  cast(report_id as varchar) as event_id,
  -- valid_at (raw) is a full ISO-8601 string that always carries a "+00:00"
  -- suffix (see fetch_preliminary_tornado_reports.parse_timestamp): IEM
  -- reports are ingested in UTC, so the local and UTC-equivalent values are
  -- identical here, unlike the NCEI side.
  cast(valid_at as timestamp) as occurred_at,
  cast(valid_at as timestamp) as occurred_at_utc,
  '+00:00' as occurred_at_utc_offset,
  upper(state) as state,
  county,
  city as begin_location,
  cast(null as varchar) as end_location,
  cast(null as varchar) as rating_code,
  cast(null as double) as path_length_miles,
  cast(null as integer) as path_width_yards,
  latitude as begin_latitude,
  longitude as begin_longitude,
  cast(null as double) as end_latitude,
  cast(null as double) as end_longitude,
  cast(null as integer) as injuries,
  cast(null as integer) as fatalities,
  cast(null as double) as property_damage_usd,
  cast(null as double) as crop_damage_usd,
  remark as event_narrative,
  source_url,
  source as report_source,
  wfo,
  fetched_at
from {{ source('raw', 'preliminary_tornado_reports') }}
where report_type = 'TORNADO'
