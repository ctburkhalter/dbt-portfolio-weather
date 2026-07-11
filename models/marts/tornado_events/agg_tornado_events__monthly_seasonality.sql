WITH regions AS (
    SELECT
        'alabama' AS region
        , occurred_at
        , rating_value
        , record_status
    FROM {{ ref('fct_tornado_events') }}
    WHERE is_alabama
    UNION ALL
    SELECT
        'dixie' AS region
        , occurred_at
        , rating_value
        , record_status
    FROM {{ ref('fct_tornado_events') }}
    WHERE is_dixie_cohort
    UNION ALL
    SELECT
        'tornado' AS region
        , occurred_at
        , rating_value
        , record_status
    FROM {{ ref('fct_tornado_events') }}
    WHERE is_tornado_cohort
)
SELECT
    region
    , EXTRACT(MONTH FROM occurred_at)::integer AS month_number
    , STRFTIME(occurred_at, '%b') AS month
    , COUNT(*) FILTER (WHERE record_status = 'confirmed') AS confirmed_tornadoes
    , COUNT(*) FILTER (WHERE record_status = 'preliminary') AS preliminary_tornado_reports
    , COUNT(*) FILTER (WHERE record_status = 'confirmed' AND rating_value >= 2) AS significant_tornadoes
FROM regions
GROUP BY 1, 2, 3
ORDER BY 1, 2
