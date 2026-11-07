#!/usr/bin/env bash
# Reproduce every result and figure from the raw data.
set -euo pipefail
cd "$(dirname "$0")"
PY=${PYTHON:-python}
$PY src/download.py      # ~170 MB from data.nlr.gov
$PY src/prepare.py       # 1-minute data -> clean hourly dataset
$PY src/explore.py       # figures/01-02
$PY src/kpi.py           # annual EU-style KPIs, figures/03
$PY src/baseline.py      # expected-overhead model, blocked cross-validation
$PY src/detector.py      # detector calibration + synthetic-fault validation
$PY src/apply.py         # detector on the real data, excess energy, figures/04
$PY src/regimes.py       # regime-aware baseline: declared mode changes, validation
$PY src/impact.py        # EUR and tCO2, real site and Grenoble what-if
$PY src/figures_en.py    # figures for the documents (docs/fig_*.png)
