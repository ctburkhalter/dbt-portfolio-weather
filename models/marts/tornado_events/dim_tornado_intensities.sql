select
    rating_code, scale_system, rating_value, intensity_class,
    wind_estimate_low_mph, wind_estimate_high_mph, wind_estimate_note
from {{ ref('tornado_intensities') }}
