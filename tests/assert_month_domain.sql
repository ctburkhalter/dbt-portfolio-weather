select * from {{ ref('agg_tornado_events__monthly_seasonality') }}
where month_number not between 1 and 12
