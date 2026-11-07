"""Baseline model: overhead power the site *should* use given IT load and weather.

Reference period = last 'normal' regime before the HVAC step (2022-07-01 .. 2024-03-27).
Validation = leave-one-month-out with a 7-day gap on each side (blocked CV), giving
out-of-fold (OOF) residuals for every month -> used to calibrate the detector.
Targets: total overhead + each component (for attribution).
"""
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import LinearRegression

ROOT = Path(__file__).resolve().parents[1]
REF = ("2022-07-01", "2024-03-27 18:00")
TARGETS = ["overhead_kw", "hvac_kw", "pump_kw", "cooling_kw"]
GAP = pd.Timedelta("7D")
# Known HVAC episodes (daily HVAC > median + 8 kW for several days), found by inspection.
# Treated as real events: excluded from training and from false-alarm calibration.
KNOWN_EVENTS = [("2023-02-28", "2023-03-02 23:00"), ("2023-03-28", "2023-04-07 23:00"),
                ("2024-02-07", "2024-02-13 23:00"), ("2024-02-16", "2024-03-27 23:00")]


def features(h: pd.DataFrame) -> pd.DataFrame:
    X = pd.DataFrame(index=h.index)
    X["it_kw"] = h.it_power_kw
    X["T_C"] = h.T_C
    X["RH"] = h.RH
    X["T_24h"] = h.T_C.rolling(24, min_periods=12).mean()
    X["hour"] = h.index.hour
    X["dow"] = h.index.day_of_week
    return X


def make_model():
    return HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05,
                                         min_samples_leaf=50, random_state=0)


def load():
    h = pd.read_parquet(ROOT / "data/processed/hourly_clean.parquet")
    return h, features(h)


def reference_hours(h):
    ref = h.loc[REF[0]:REF[1]]
    ref = ref[ref.valid]
    for a, b in KNOWN_EVENTS:
        ref = ref.drop(ref.loc[a:b].index)
    return ref


def oof_residuals(h, X, target):
    ref = reference_hours(h)
    Xr, yr = X.loc[ref.index], ref[target]
    pred = pd.Series(np.nan, index=ref.index)
    pred_lin = pred.copy()
    for m in ref.index.to_period("M").unique():
        test = ref.index.to_period("M") == m
        t0, t1 = ref.index[test].min(), ref.index[test].max()
        train = (ref.index < t0 - GAP) | (ref.index > t1 + GAP)
        mdl = make_model().fit(Xr[train], yr[train])
        pred[test] = mdl.predict(Xr[test])
        cols = ["it_kw", "T_C", "T_24h"]
        ok = Xr[cols].notna().all(axis=1)
        lin = LinearRegression().fit(Xr.loc[train & ok, cols], yr[train & ok])
        pred_lin[test & ok] = lin.predict(Xr.loc[test & ok, cols])
    return pd.DataFrame({"y": yr, "pred": pred, "pred_lin": pred_lin})


def fit_reference(h, X, target):
    ref = reference_hours(h)
    return make_model().fit(X.loc[ref.index], ref[target])


def main():
    h, X = load()
    out = ROOT / "results"
    rows = []
    for t in TARGETS:
        r = oof_residuals(h, X, t)
        r.to_parquet(out / f"oof_{t}.parquet")
        for name, p in [("GBM", r.pred), ("linear", r.pred_lin)]:
            e = (r.y - p).dropna()
            d = e.resample("D").mean().dropna()
            rows.append(dict(target=t, model=name, mean_y=r.y.mean(), MAE_h=e.abs().mean(),
                             R2=1 - (e**2).sum() / ((r.y.loc[e.index] - r.y.loc[e.index].mean())**2).sum(),
                             sd_daily=d.std(), bias=e.mean()))
    s = pd.DataFrame(rows).round(3)
    s.to_csv(out / "baseline_skill.csv", index=False)
    print(s.to_string(index=False))


if __name__ == "__main__":
    main()
