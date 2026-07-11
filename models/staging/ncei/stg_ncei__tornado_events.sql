WITH source AS (
    SELECT * FROM {{ source('ncei', 'tornado_events') }}
)
, renamed AS (
    SELECT
        county
        , begin_location
        , end_location
        , property_damage_usd
        , crop_damage_usd
        , event_narrative AS narrative
        , source_url
        , CAST(event_id AS varchar) AS event_id
        , CAST(REGEXP_REPLACE(occurred_at, '[+-][0-9]{2}:[0-9]{2}$', '') AS timestamp) AS occurred_at
        , CAST(occurred_at AS timestamp) AS occurred_at_utc
        , UPPER(state) AS state
        , REGEXP_EXTRACT(occurred_at, '([+-][0-9]{2}:[0-9]{2})$', 1) AS occurred_at_utc_offset
        , UPPER(tor_f_scale) AS rating_code
        , TRY_CAST(tor_length AS double) AS path_length_miles
        , TRY_CAST(tor_width AS integer) AS path_width_yards
        , TRY_CAST(begin_lat AS double) AS begin_latitude
        , TRY_CAST(begin_lon AS double) AS begin_longitude
        , TRY_CAST(end_lat AS double) AS end_latitude
        , TRY_CAST(end_lon AS double) AS end_longitude
        , COALESCE(TRY_CAST(injuries_direct AS integer), 0) AS injuries
        , COALESCE(TRY_CAST(deaths_direct AS integer), 0) AS fatalities
    FROM source
    WHERE event_type = 'Tornado'
)
SELECT * FROM renamed
