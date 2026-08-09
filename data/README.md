# Data notes

The raw GA4 event tables are hosted in BigQuery and are not copied into this repository.

- `source/` contains small aggregated exports produced by the SQL files.
- `processed/` contains tables created by `scripts/build_analysis.py`.
- `powerbi/` contains the same decision-ready tables used by the PBIP semantic model.

Official source: `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`.

