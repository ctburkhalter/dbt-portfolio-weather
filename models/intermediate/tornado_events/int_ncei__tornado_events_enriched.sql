SELECT
    event.*
    , {{ cohort_flags('event.state') }}
FROM {{ ref('stg_ncei__tornado_events') }} AS event
