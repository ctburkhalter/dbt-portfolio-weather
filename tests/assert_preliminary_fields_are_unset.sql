select * from {{ ref('fct_tornado_events') }}
where record_status = 'preliminary' and (
  rating_code is not null or scale_system is not null or rating_value is not null
  or wind_estimate_low_mph is not null or wind_estimate_high_mph is not null
  or path_length_miles is not null or path_width_yards is not null
  or end_latitude is not null or end_longitude is not null
  or injuries is not null or fatalities is not null
  or property_damage_usd is not null or crop_damage_usd is not null
)
