with confirmed_cutoff as (
    select max(occurred_at_utc) as max_confirmed_occurred_at_utc
    from {{ ref('int_ncei__tornado_events_enriched') }}
),
confirmed as (
    select
        event.event_id, event.occurred_at,
        event.occurred_at_utc, event.occurred_at_utc_offset, event.state,
        event.county, event.begin_location, event.end_location, intensity.rating_code,
        intensity.scale_system, intensity.rating_value, intensity.intensity_class,
        intensity.wind_estimate_low_mph, intensity.wind_estimate_high_mph,
        intensity.wind_estimate_note, event.path_length_miles,
        event.path_width_yards, event.begin_latitude, event.begin_longitude,
        event.end_latitude, event.end_longitude, event.injuries,
        event.fatalities, event.property_damage_usd, event.crop_damage_usd,
        event.narrative, event.source_url, event.is_alabama,
        event.is_dixie_cohort, event.is_tornado_cohort, cast(null as varchar) as source_attribution,
        cast(null as varchar) as wfo, 'confirmed' as record_status,
        'ncei_storm_events' as source_system, false as is_surveyed_track,
        'ncei_storm_events:' || event.event_id as event_key
    from {{ ref('int_ncei__tornado_events_enriched') }} as event
    left join {{ ref('dim_tornado_intensities') }} as intensity
        on {{ normalized_rating_code('event.rating_code') }} = intensity.rating_code
),
preliminary as (
    select
        event.event_id, event.occurred_at,
        event.occurred_at_utc, event.occurred_at_utc_offset, event.state,
        event.county, event.begin_location, event.end_location, event.rating_code,
        cast(null as varchar) as scale_system, cast(null as integer) as rating_value,
        cast('Preliminary report' as varchar) as intensity_class, cast(null as integer) as wind_estimate_low_mph,
        cast(null as integer) as wind_estimate_high_mph,
        cast('Preliminary Local Storm Reports do not include a damage-based F or EF wind estimate.' as varchar)
            as wind_estimate_note,
        event.path_length_miles,
        event.path_width_yards, event.begin_latitude, event.begin_longitude,
        event.end_latitude, event.end_longitude, event.injuries,
        event.fatalities, event.property_damage_usd, event.crop_damage_usd,
        event.narrative, event.source_url, event.is_alabama,
        event.is_dixie_cohort, event.is_tornado_cohort, event.source_attribution,
        event.wfo, 'preliminary' as record_status, 'iem_lsr' as source_system,
        false as is_surveyed_track, 'iem_lsr:' || event.event_id as event_key
    from {{ ref('int_iem__tornado_reports_conformed') }} as event
    cross join confirmed_cutoff
    where event.occurred_at_utc > confirmed_cutoff.max_confirmed_occurred_at_utc
)
select
    event_key, event_id, occurred_at, occurred_at_utc, occurred_at_utc_offset,
    state, county, begin_location, end_location, rating_code, scale_system,
    rating_value, intensity_class, wind_estimate_low_mph, wind_estimate_high_mph,
    wind_estimate_note, path_length_miles, path_width_yards, begin_latitude,
    begin_longitude, end_latitude, end_longitude, injuries, fatalities,
    property_damage_usd, crop_damage_usd, narrative, source_url, is_alabama,
    is_dixie_cohort, is_tornado_cohort, source_attribution, wfo, record_status,
    source_system, is_surveyed_track
from confirmed
union all
select
    event_key, event_id, occurred_at, occurred_at_utc, occurred_at_utc_offset,
    state, county, begin_location, end_location, rating_code, scale_system,
    rating_value, intensity_class, wind_estimate_low_mph, wind_estimate_high_mph,
    wind_estimate_note, path_length_miles, path_width_yards, begin_latitude,
    begin_longitude, end_latitude, end_longitude, injuries, fatalities,
    property_damage_usd, crop_damage_usd, narrative, source_url, is_alabama,
    is_dixie_cohort, is_tornado_cohort, source_attribution, wfo, record_status,
    source_system, is_surveyed_track
from preliminary
