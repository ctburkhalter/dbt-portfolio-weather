{% macro cohort_flags(state_column) -%}
  {{ state_column }} = 'AL' as is_alabama,
  {{ state_column }} in ('AL', 'AR', 'GA', 'LA', 'MS', 'TN') as is_dixie_cohort,
  {{ state_column }} in ('CO', 'IA', 'KS', 'NE', 'OK', 'SD', 'TX') as is_tornado_cohort
{%- endmacro %}
