with source as (
    select * from {{ source('iem', 'preliminary_tornado_reports') }}
),
renamed as (
    select
        cast(report_id as varchar) as event_id, cast(valid_at as timestamp) as occurred_at,
        cast(valid_at as timestamp) as occurred_at_utc, '+00:00' as occurred_at_utc_offset,
        county, city as begin_location, cast(null as varchar) as end_location, cast(null as varchar) as rating_code,
        cast(null as double) as path_length_miles, cast(null as integer) as path_width_yards,
        latitude as begin_latitude, longitude as begin_longitude,
        cast(null as double) as end_latitude, cast(null as double) as end_longitude,
        cast(null as integer) as injuries, cast(null as integer) as fatalities,
        cast(null as double) as property_damage_usd, cast(null as double) as crop_damage_usd,
        remark as narrative, source_url, source as source_attribution,
        wfo, fetched_at, upper(state) as state
    from source
    where report_type = 'TORNADO'
)
select * from renamed
