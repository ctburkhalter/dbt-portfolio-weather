SELECT
    EXTRACT(YEAR FROM occurred_at)::integer AS year
    , COUNT(*) FILTER (WHERE record_status = 'confirmed') AS confirmed_tornadoes
    , COUNT(*) FILTER (WHERE record_status = 'preliminary') AS preliminary_tornado_reports
    , COUNT(*) FILTER (WHERE record_status = 'confirmed' AND rating_value >= 2) AS significant_tornadoes
FROM {{ ref('fct_tornado_events') }}
WHERE is_alabama
GROUP BY 1
ORDER BY 1
