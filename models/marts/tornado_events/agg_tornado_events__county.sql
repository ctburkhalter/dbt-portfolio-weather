SELECT
    state
    , county
    , COUNT(*) FILTER (WHERE record_status = 'confirmed') AS confirmed_tornadoes
    , COUNT(*) FILTER (WHERE record_status = 'preliminary') AS preliminary_tornado_reports
    , COUNT(*) FILTER (WHERE record_status = 'confirmed' AND rating_value >= 2) AS significant_tornadoes
    , SUM(injuries) FILTER (WHERE record_status = 'confirmed') AS injuries
    , MAX_BY(rating_code, rating_value) FILTER (WHERE record_status = 'confirmed') AS max_rating
FROM {{ ref('fct_tornado_events') }}
WHERE is_alabama
GROUP BY state, county
ORDER BY confirmed_tornadoes DESC, state ASC, county ASC
