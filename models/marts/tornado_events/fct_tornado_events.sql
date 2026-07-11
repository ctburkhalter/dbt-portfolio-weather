WITH confirmed_cutoff AS (
    SELECT MAX(occurred_at_utc) AS max_confirmed_occurred_at_utc
    FROM {{ ref('int_ncei__tornado_events_enriched') }}
)
, confirmed AS (
    SELECT
        event.event_id
        , event.occurred_at
        , event.occurred_at_utc
        , event.occurred_at_utc_offset
        , event.state
        , event.county
        , event.begin_location
        , event.end_location
        , intensity.rating_code
        , intensity.scale_system
        , intensity.rating_value
        , intensity.intensity_class
        , intensity.wind_estimate_low_mph
        , intensity.wind_estimate_high_mph
        , intensity.wind_estimate_note
        , event.path_length_miles
        , event.path_width_yards
        , event.begin_latitude
        , event.begin_longitude
        , event.end_latitude
        , event.end_longitude
        , event.injuries
        , event.fatalities
        , event.property_damage_usd
        , event.crop_damage_usd
        , event.narrative
        , event.source_url
        , event.is_alabama
        , event.is_dixie_cohort
        , event.is_tornado_cohort
        , 'confirmed' AS record_status
        , 'ncei_storm_events' AS source_system
        , FALSE AS is_surveyed_track
        , CAST(NULL AS varchar) AS source_attribution
        , CAST(NULL AS varchar) AS wfo
        , 'ncei_storm_events:' || event.event_id AS event_key
    FROM {{ ref('int_ncei__tornado_events_enriched') }} AS event
    LEFT JOIN {{ ref('dim_tornado_intensities') }} AS intensity
        ON {{ normalized_rating_code('event.rating_code') }} = intensity.rating_code
)
, preliminary AS (
    SELECT
        event.event_id
        , event.occurred_at
        , event.occurred_at_utc
        , event.occurred_at_utc_offset
        , event.state
        , event.county
        , event.begin_location
        , event.end_location
        , event.rating_code
        , event.path_length_miles
        , event.path_width_yards
        , event.begin_latitude
        , event.begin_longitude
        , event.end_latitude
        , event.end_longitude
        , event.injuries
        , event.fatalities
        , event.property_damage_usd
        , event.crop_damage_usd
        , event.narrative
        , event.source_url
        , event.is_alabama
        , event.is_dixie_cohort
        , event.is_tornado_cohort
        , event.source_attribution
        , event.wfo
        , 'preliminary' AS record_status
        , 'iem_lsr' AS source_system
        , FALSE AS is_surveyed_track
        , CAST(NULL AS varchar) AS scale_system
        , CAST(NULL AS integer) AS rating_value
        , CAST('Preliminary report' AS varchar) AS intensity_class
        , CAST(NULL AS integer) AS wind_estimate_low_mph
        , CAST(NULL AS integer) AS wind_estimate_high_mph
        , CAST('Preliminary Local Storm Reports do not include a damage-based F or EF wind estimate.' AS varchar)
            AS wind_estimate_note
        , 'iem_lsr:' || event.event_id AS event_key
    FROM {{ ref('int_iem__tornado_reports_conformed') }} AS event
    CROSS JOIN confirmed_cutoff
    WHERE event.occurred_at_utc > confirmed_cutoff.max_confirmed_occurred_at_utc
)
SELECT
    event_key
    , event_id
    , occurred_at
    , occurred_at_utc
    , occurred_at_utc_offset
    , state
    , county
    , begin_location
    , end_location
    , rating_code
    , scale_system
    , rating_value
    , intensity_class
    , wind_estimate_low_mph
    , wind_estimate_high_mph
    , wind_estimate_note
    , path_length_miles
    , path_width_yards
    , begin_latitude
    , begin_longitude
    , end_latitude
    , end_longitude
    , injuries
    , fatalities
    , property_damage_usd
    , crop_damage_usd
    , narrative
    , source_url
    , is_alabama
    , is_dixie_cohort
    , is_tornado_cohort
    , source_attribution
    , wfo
    , record_status
    , source_system
    , is_surveyed_track
FROM confirmed
UNION ALL
SELECT
    event_key
    , event_id
    , occurred_at
    , occurred_at_utc
    , occurred_at_utc_offset
    , state
    , county
    , begin_location
    , end_location
    , rating_code
    , scale_system
    , rating_value
    , intensity_class
    , wind_estimate_low_mph
    , wind_estimate_high_mph
    , wind_estimate_note
    , path_length_miles
    , path_width_yards
    , begin_latitude
    , begin_longitude
    , end_latitude
    , end_longitude
    , injuries
    , fatalities
    , property_damage_usd
    , crop_damage_usd
    , narrative
    , source_url
    , is_alabama
    , is_dixie_cohort
    , is_tornado_cohort
    , source_attribution
    , wfo
    , record_status
    , source_system
    , is_surveyed_track
FROM preliminary
