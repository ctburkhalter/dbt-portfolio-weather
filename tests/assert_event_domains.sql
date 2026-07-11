select * from {{ ref('fct_tornado_events') }} where
  state not in ('AL','AR','CO','GA','IA','KS','LA','MS','NE','OK','SD','TN','TX')
  or occurred_at_utc_offset is null
  or not regexp_matches(occurred_at_utc_offset, '^[+-][0-9]{2}:[0-9]{2}$')
  or begin_latitude not between -90 and 90
  or begin_longitude not between -180 and 180
  or end_latitude not between -90 and 90
  or end_longitude not between -180 and 180
  or ((begin_latitude is null) != (begin_longitude is null))
  or ((end_latitude is null) != (end_longitude is null))
  or (record_status = 'confirmed' and source_system != 'ncei_storm_events')
  or (record_status = 'preliminary' and source_system != 'iem_lsr')
  or is_surveyed_track
