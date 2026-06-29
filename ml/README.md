# ML — V7 Chargeback Model

`v7_chargeback_model.ipynb` is the training/backtest notebook for the V7
stacked-generalization model that powers the dashboard's ML tab.

**Outputs are intentionally stripped and no data is included** — the notebook reads
confidential client files (Gross Sales, CB Detail, Daily Sales) that are excluded from
this repository. It is published to show the modelling approach, not to be re-run as-is.

See the [main README](../README.md#the-ml-model--v7-stacked-generalization) for the
architecture (5-layer stacked generalization) and backtest results (R² 0.95, 85.5% of
CB dollars within ±10%).

## Pipeline overview

1. Load & dedup raw chargeback + sales data; build monthly per-pair features.
2. Train the 14-model base zoo; generate out-of-fold predictions.
3. Build pair-specific meta-features; train the two XGBoost stackers (raw + log).
4. Apply online bias correction and confidence-weighted blending.
5. Backtest (`v7_results.csv`) and forward-predict (`predictions_{month}_v7.csv`).
