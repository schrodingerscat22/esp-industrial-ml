# Data catalog

This file describes processed datasets and intermediate files used in the ESP dust concentration prediction project.

## 1. Clean datasets

### `dataset_clean.parquet`

Initial cleaned dataset after loading and basic preprocessing.

Used as an intermediate file. Not recommended as the main input for modelling after later processing steps were introduced.

### `df_model_clean_v1.parquet`

Main cleaned modelling dataset before feature engineering.

Contains:
- timestamp index,
- selected process input signals,
- target variable,
- no missing values after removal of rows with missing boiler load signals,
- original signal names as tag IDs.

Target:
- `008A01345` — Pył BC1 Stężenie aktualne `[mg/Nm3]`

Use this file for:
- exploratory analysis,
- process interpretation,
- energy/emission analysis,
- event analysis,
- creating new features from original signals.

Do not use this file directly for final feature-engineered model training unless features are generated again.

---

## 2. Tag metadata and classification

### `tag_mapping.csv`

Original tag description table.

Contains tag IDs, descriptions, symbols and units.

### `tag_classification.xlsx`

Working version of manually classified tags.

### `tag_classification_v1.xlsx`

Versioned tag classification used in the current modelling workflow.

Contains:
- tag,
- description,
- symbol,
- unit,
- category,
- role,
- comment.

Use this file as the reference mapping for interpreting model features and signal categories.

---

## 3. Feature engineering datasets

### `df_feature_engineered_v1.parquet`

Full dataset after feature engineering.

Contains:
- original signals,
- lag features,
- rolling mean/std features,
- diff features,
- target,
- technical columns if present.

This is the full feature-engineered dataset before separating X and y.

### `X_feature_engineered_v1.parquet`

Feature matrix for the full feature engineering model.

Contains:
- raw features,
- lag features,
- rolling features,
- diff features.

Does not contain the target variable.

Used for:
- XGBoost full feature engineering model.

### `y_feature_engineered_v1.parquet`

Target vector corresponding to `X_feature_engineered_v1.parquet`.

Target:
- `008A01345` — dust concentration after ESP.

### `feature_list_v1.csv`

List of feature names used in `X_feature_engineered_v1.parquet`.

Useful for:
- checking model inputs,
- reproducing experiments,
- interpreting feature importance.

---

## 4. Rapping event analysis

### `rapping_event_analysis_v1.parquet`

Event-level dataset for rapping signal analysis.

Each row corresponds to one detected rapping start event.

Contains:
- event time,
- rapping tag,
- dust at event,
- maximum and mean dust in time windows after event.

Used to analyze the relationship between rapping events and dust concentration peaks.

### `rapping_window_probability_v1.csv`

Summary table with probabilities of dust threshold exceedance after rapping events.

Includes probabilities such as:
- `P_max_dust_gt_20`,
- `P_max_dust_gt_40`,
- `P_max_dust_gt_60`.

Important result:
- `008B05154` — collecting electrode rapping zone 3 shows the strongest relation with dust peaks.

### `rapping_profile_summary_v1.csv`

Summary of event-aligned dust profiles for each rapping signal.

Contains:
- number of events,
- baseline dust level,
- peak dust level,
- delta between peak and baseline,
- time to peak.

Important result:
- for `008B05154`, median dust increased from about 11 to 42 mg/Nm3 around 1.2 min after rapping start.

### `rapping_features_v1.parquet`

Time-indexed features related to critical rapping event `008B05154`.

Contains:
- `rapping_3_collecting_start`,
- `minutes_since_rapping_3_collecting_start_0_5`,
- `is_within_5min_after_rapping_3_collecting`.

Used for:
- adding rapping-related features to prediction models,
- masking disturbed periods after rapping.

---

## 5. Base emission datasets

### `base_emission_mask_no_008B05154_0_3min_v1.parquet`

Boolean mask identifying samples considered representative of base emission.

Definition:
- `True` means sample is outside the 0–3 min window after start of `008B05154`,
- `False` means sample belongs to the disturbed period after collecting electrode rapping in zone 3.

Used for:
- filtering out rapping-induced dust peak periods.

### `X_feature_engineered_base_emission_v1.parquet`

Feature matrix after removing samples from 0–3 min after `008B05154` rapping start.

Used for:
- modelling base dust emission without major rapping-induced peaks.

### `y_feature_engineered_base_emission_v1.parquet`

Target vector corresponding to `X_feature_engineered_base_emission_v1.parquet`.

Used for:
- base emission model training and evaluation.

---

## 6. Model results

### `model_results_feature_engineering_v1.csv`

Summary of models trained during feature engineering experiments.

Contains results such as:
- baseline model,
- full feature engineering model,
- no-diff variant,
- regularized model.

Main result:
- XGBoost full FE: MAE ≈ 1.393 mg/Nm3, R2 ≈ 0.723.

### `model_results_base_emission_v1.csv`

Summary of model trained after removing 0–3 min periods after `008B05154` rapping start.

Used for:
- comparison of full emission model vs base emission model.