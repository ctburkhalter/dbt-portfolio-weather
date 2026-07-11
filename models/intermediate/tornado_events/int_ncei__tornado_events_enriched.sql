select event.*, {{ cohort_flags('event.state') }}
from {{ ref('stg_ncei__tornado_events') }} as event
