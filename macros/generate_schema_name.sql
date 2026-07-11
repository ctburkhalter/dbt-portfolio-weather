{% macro generate_schema_name(custom_schema_name, node) -%}
  {{ target.schema }}{% if custom_schema_name is not none %}_{{ custom_schema_name | trim }}{% endif %}
{%- endmacro %}
