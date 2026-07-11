with source as (
    select * from {{ source('ncei', 'tornado_events') }}
),
renamed as (
    select
        cast(event_id as varchar) as event_id,
        county,
        cast(regexp_replace(occurred_at, '[+-][0-9]{2}:[0-9]{2}$', '') as timestamp) as occurred_at,
        cast(occurred_at as timestamp) as occurred_at_utc,
        begin_location,
        end_location,
        property_damage_usd, crop_damage_usd, event_narrative as narrative,
        source_url,
        upper(state) as state,
        regexp_extract(occurred_at, '([+-][0-9]{2}:[0-9]{2})$', 1) as occurred_at_utc_offset,
        upper(tor_f_scale) as rating_code,
        try_cast(tor_length as double) as path_length_miles, try_cast(tor_width as integer) as path_width_yards,
        try_cast(begin_lat as double) as begin_latitude,
        try_cast(begin_lon as double) as begin_longitude,
        try_cast(end_lat as double) as end_latitude,
        try_cast(end_lon as double) as end_longitude,
        coalesce(try_cast(injuries_direct as integer), 0) as injuries,
        coalesce(try_cast(deaths_direct as integer), 0) as fatalities
    from source
    where event_type = 'Tornado'
)
select * from renamed
