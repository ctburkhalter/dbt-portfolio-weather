SELECT
    event.*
    , {{ cohort_flags('event.state') }}
FROM {{ ref('stg_iem__preliminary_tornado_reports') }} AS event
