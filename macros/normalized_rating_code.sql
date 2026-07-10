{% macro normalized_rating_code(column) -%}
  case
    when regexp_matches(trim({{ column }}), '^EF[0-5]$') then trim({{ column }})
    when regexp_matches(trim({{ column }}), '^F[0-5]$') then trim({{ column }})
    else 'Unknown'
  end
{%- endmacro %}
