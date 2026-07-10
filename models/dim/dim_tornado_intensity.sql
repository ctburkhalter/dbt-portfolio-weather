with ratings as (
  select distinct
    case
      when regexp_matches(trim(rating_code), '^EF[0-5]$') then trim(rating_code)
      when regexp_matches(trim(rating_code), '^F[0-5]$') then trim(rating_code)
      else 'Unknown'
    end as rating_code
  from {{ ref('src_ncei__tornado_events') }}
), normalized as (
  select
    rating_code,
    case
      when regexp_matches(rating_code, '^EF[0-5]$') then 'EF'
      when regexp_matches(rating_code, '^F[0-5]$') then 'F'
      else 'Unknown'
    end as scale_system,
    try_cast(regexp_extract(rating_code, '([0-5])$', 1) as integer) as rating_value
  from ratings
)
select
  rating_code,
  scale_system,
  rating_value,
  case
    when rating_value in (0, 1) then 'Weak'
    when rating_value in (2, 3) then 'Strong'
    when rating_value in (4, 5) then 'Violent'
    else 'Unknown'
  end as intensity_class,
  case
    when scale_system = 'EF' and rating_value = 0 then 65
    when scale_system = 'EF' and rating_value = 1 then 86
    when scale_system = 'EF' and rating_value = 2 then 111
    when scale_system = 'EF' and rating_value = 3 then 136
    when scale_system = 'EF' and rating_value = 4 then 166
    when scale_system = 'EF' and rating_value = 5 then 201
    when scale_system = 'F' and rating_value = 0 then 40
    when scale_system = 'F' and rating_value = 1 then 73
    when scale_system = 'F' and rating_value = 2 then 113
    when scale_system = 'F' and rating_value = 3 then 158
    when scale_system = 'F' and rating_value = 4 then 207
    when scale_system = 'F' and rating_value = 5 then 260
  end as wind_estimate_low_mph,
  case
    when scale_system = 'EF' and rating_value = 0 then 85
    when scale_system = 'EF' and rating_value = 1 then 110
    when scale_system = 'EF' and rating_value = 2 then 135
    when scale_system = 'EF' and rating_value = 3 then 165
    when scale_system = 'EF' and rating_value = 4 then 200
    when scale_system = 'EF' and rating_value = 5 then null
    when scale_system = 'F' and rating_value = 0 then 72
    when scale_system = 'F' and rating_value = 1 then 112
    when scale_system = 'F' and rating_value = 2 then 157
    when scale_system = 'F' and rating_value = 3 then 206
    when scale_system = 'F' and rating_value = 4 then 260
    when scale_system = 'F' and rating_value = 5 then 318
  end as wind_estimate_high_mph,
  case
    when scale_system = 'EF' then 'EF-scale three-second gust estimate inferred from damage, not a direct wind measurement.'
    when scale_system = 'F' then 'F-scale wind estimate inferred from damage, not a direct wind measurement.'
    else 'No rating-based wind estimate is available.'
  end as wind_estimate_note
from normalized
