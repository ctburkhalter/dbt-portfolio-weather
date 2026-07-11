{#
  Shared column descriptions for concepts that repeat with identical meaning
  across multiple models, mainly the three fact tables (fct_tornado_events,
  fct_preliminary_tornado_reports, fct_tornado_events_current) and, where the
  value is a straight passthrough with no added transformation, their
  upstream src models. Referenced from models.yml via {{ doc('block_name') }}
  so each concept is written once instead of three or more times.

  Not used for columns whose meaning genuinely differs by layer or source
  (for example src_ncei__tornado_events.rating_code, which is the raw,
  unnormalized source value, versus the fact tables' rating_code, which is
  normalized through dim_tornado_intensity) or for dim_tornado_intensity's
  own rating columns (that model has no concept of confirmed-versus-
  preliminary rows at all, so the fact-table framing below does not fit).
#}

{% docs state %}
Two-letter state code.
{% enddocs %}

{% docs county %}
County or zone name for the event location, as reported by the source: NCEI's CZ_NAME field for confirmed rows, IEM's COUNTY field for preliminary rows. Not standardized beyond source casing.
{% enddocs %}

{% docs begin_location %}
Named location nearest the event's starting point, as reported by the source (NCEI's BEGIN_LOCATION or IEM's city field). Not a standardized geocoded address.
{% enddocs %}

{% docs end_location %}
Named location nearest the event's ending point, as reported by NCEI (END_LOCATION). Null for preliminary IEM reports, which do not include an end location.
{% enddocs %}

{% docs rating_code %}
Normalized F or EF damage-based rating code (for example F3, EF2), or the literal value Unknown when a confirmed event's source rating is missing or unrecognized (see dim_tornado_intensity). Null, not Unknown, for preliminary IEM reports, which do not include a rating at all.
{% enddocs %}

{% docs scale_system %}
Which damage scale the rating uses: F (pre-2007 Fujita scale) or EF (Enhanced Fujita scale, 2007 onward), or Unknown when the rating is missing or unrecognized. Null for preliminary IEM reports.
{% enddocs %}

{% docs rating_value %}
Numeric severity within the F or EF scale (0-5), parsed from rating_code. Null when the scale is Unknown or the row is a preliminary IEM report.
{% enddocs %}

{% docs intensity_class %}
Three-tier grouping of rating_value: Weak (0-1), Strong (2-3), or Violent (4-5), or Unknown when no rating value is available. Preliminary IEM reports carry the literal value 'Preliminary report' instead, since no rating exists to classify.
{% enddocs %}

{% docs wind_estimate_low_mph %}
Low end of the three-second gust wind speed range associated with rating_value (see dim_tornado_intensity), inferred from damage rather than measured directly. Null when no rating value is available, including all preliminary IEM reports.
{% enddocs %}

{% docs wind_estimate_high_mph %}
High end of the three-second gust wind speed range associated with rating_value (see dim_tornado_intensity), inferred from damage rather than measured directly. Null when no rating value is available (including all preliminary IEM reports) and for EF5, whose high end is unbounded by definition.
{% enddocs %}

{% docs wind_estimate_note %}
Caveat describing how the wind estimate for this row was derived: a damage-based estimate for a confirmed EF or F rating, or an explanatory note when no rating-based estimate applies (an unrated confirmed event, or a preliminary IEM report, which is never rated).
{% enddocs %}

{% docs path_length_miles %}
Tornado path length in miles, as reported by NCEI (TOR_LENGTH). Null for preliminary IEM reports, which are point reports without surveyed path geometry.
{% enddocs %}

{% docs path_width_yards %}
Tornado path width in yards, as reported by NCEI (TOR_WIDTH). Null for preliminary IEM reports, which are point reports without surveyed path geometry.
{% enddocs %}

{% docs begin_latitude %}
Latitude of the event's starting point, as reported by the source (NCEI's BEGIN_LAT or IEM's LAT). An endpoint coordinate, not a surveyed track vertex.
{% enddocs %}

{% docs begin_longitude %}
Longitude of the event's starting point, as reported by the source (NCEI's BEGIN_LON or IEM's LON). An endpoint coordinate, not a surveyed track vertex.
{% enddocs %}

{% docs end_latitude %}
Latitude of the event's ending point, as reported by NCEI (END_LAT). An endpoint coordinate, not a surveyed track vertex. Null for preliminary IEM reports, which are point reports with no ending coordinate.
{% enddocs %}

{% docs end_longitude %}
Longitude of the event's ending point, as reported by NCEI (END_LON). An endpoint coordinate, not a surveyed track vertex. Null for preliminary IEM reports, which are point reports with no ending coordinate.
{% enddocs %}

{% docs injuries %}
Direct injuries attributed to the event, as reported by NCEI (INJURIES_DIRECT) and coalesced to 0 when missing or unparseable. Does not include indirect injuries. Null for preliminary IEM reports, which do not carry casualty counts at all.
{% enddocs %}

{% docs fatalities %}
Direct fatalities attributed to the event, as reported by NCEI (DEATHS_DIRECT) and coalesced to 0 when missing or unparseable. Does not include indirect fatalities. Null for preliminary IEM reports, which do not carry casualty counts at all.
{% enddocs %}

{% docs property_damage_usd %}
Estimated property damage in US dollars, as reported by NCEI (DAMAGE_PROPERTY) and parsed from its K/M/B-suffixed shorthand (see load_ncei_events.parse_damage). Null when NCEI reports the damage as unknown, and for preliminary IEM reports, which do not carry damage estimates.
{% enddocs %}

{% docs crop_damage_usd %}
Estimated crop damage in US dollars, as reported by NCEI (DAMAGE_CROPS) and parsed from its K/M/B-suffixed shorthand (see load_ncei_events.parse_damage). Null when NCEI reports the damage as unknown, and for preliminary IEM reports, which do not carry damage estimates.
{% enddocs %}

{% docs narrative %}
Free-text event narrative as reported by the source: NCEI's EVENT_NARRATIVE for confirmed events, the Local Storm Report remark for preliminary IEM reports.
{% enddocs %}

{% docs source_url %}
Link to the source program for this row, not a per-event permalink: NCEI's Storm Events landing page for confirmed rows, the IEM Local Storm Report request page for preliminary rows.
{% enddocs %}

{% docs is_alabama %}
True when state = AL.
{% enddocs %}

{% docs is_dixie_cohort %}
True when state is in the project-defined Dixie comparison cohort (AL, AR, GA, LA, MS, TN).
{% enddocs %}

{% docs is_tornado_cohort %}
True when state is in the project-defined Tornado comparison cohort (CO, IA, KS, NE, OK, SD, TX).
{% enddocs %}

{% docs wfo %}
National Weather Service Weather Forecast Office associated with a preliminary IEM report. Null for confirmed NCEI rows, which do not carry this attribution.
{% enddocs %}

{% docs source_attribution %}
Free-text label identifying who filed a preliminary report (for example a trained spotter, law enforcement, media, or the public), as reported by the Iowa State Mesonet Local Storm Report source (IEM's SOURCE field). Null for confirmed NCEI rows, which do not carry this attribution.
{% enddocs %}
