select
  alert_id,
  scope,
  affects_dothan,
  event,
  headline,
  sent_at,
  effective_at,
  expires_at,
  severity,
  certainty,
  urgency,
  area_description,
  detection,
  damage_threat,
  motion_description,
  source_url,
  ingested_at
from {{ source('raw', 'nws_active_alerts') }}
where event in ('Tornado Warning', 'Tornado Watch')
