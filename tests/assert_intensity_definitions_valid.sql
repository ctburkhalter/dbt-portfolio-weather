select * from {{ ref('dim_tornado_intensities') }}
where (scale_system in ('F', 'EF') and rating_value not between 0 and 5)
   or (scale_system = 'Unknown' and rating_value is not null)
   or wind_estimate_low_mph < 0
   or wind_estimate_high_mph < wind_estimate_low_mph
