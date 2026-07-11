WITH source AS (
    SELECT * FROM {{ source('iem', 'preliminary_tornado_reports') }}
)
, renamed AS (
    SELECT
        '+00:00' AS occurred_at_utc_offset
        , county
        , city AS begin_location
        , latitude AS begin_latitude
        , longitude AS begin_longitude
        , remark AS narrative
        , source_url
        , source AS source_attribution
        , wfo
        , fetched_at
        , CAST(report_id AS varchar) AS event_id
        , CAST(valid_at AS timestamp) AS occurred_at
        , CAST(valid_at AS timestamp) AS occurred_at_utc
        , CAST(NULL AS varchar) AS end_location
        , CAST(NULL AS varchar) AS rating_code
        , CAST(NULL AS double) AS path_length_miles
        , CAST(NULL AS integer) AS path_width_yards
        , CAST(NULL AS double) AS end_latitude
        , CAST(NULL AS double) AS end_longitude
        , CAST(NULL AS integer) AS injuries
        , CAST(NULL AS integer) AS fatalities
        , CAST(NULL AS double) AS property_damage_usd
        , CAST(NULL AS double) AS crop_damage_usd
        , UPPER(state) AS state
    FROM source
    WHERE report_type = 'TORNADO'
)
SELECT * FROM renamed
