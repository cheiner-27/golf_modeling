"""
Feature engineering modules. Each module builds one logical group of
features keyed by (event_id_year, dg_id), per the naming scheme in
reports/feature_groups.yaml.

Leakage rule: every aggregation uses only rounds whose end_date is
strictly less than the row's event start_date.
"""
