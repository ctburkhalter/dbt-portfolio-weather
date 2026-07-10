select *
from {{ ref('fct_tornado_events_current') }}
where record_status = 'preliminary'
  and (
    rating_code is not null
    or scale_system is not null
    or rating_value is not null
    or wind_estimate_low_mph is not null
    or wind_estimate_high_mph is not null
  )
