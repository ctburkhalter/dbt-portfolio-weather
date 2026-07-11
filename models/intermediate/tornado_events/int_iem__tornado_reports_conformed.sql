select event.*, {{ cohort_flags('event.state') }}
from {{ ref('stg_iem__preliminary_tornado_reports') }} as event
