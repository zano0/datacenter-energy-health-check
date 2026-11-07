"""Detector + synthetic-fault validation.

Detector: one-sided CUSUM on standardized DAILY residuals (actual - expected), run in
parallel on total overhead and on each component (HVAC, pumps, cooling). An alarm on
any of them is an alarm; the component that fires first is the attribution.
Threshold h is calibrated on clean out-of-fold residuals for a target false-alarm rate.
Validation: inject step/ramp faults into the clean OOF data and measure detection
probability and delay as a function of fault size.
"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
COMPS = ["overhead_kw", "hvac_kw", "pump_kw", "cooling_kw"]
K = 0.5            # CUSUM allowance (in sigma units)
FA_TARGET = 1 / 3  # max false alarms per month, all detectors together (= 1 per quarter)
HORIZON = 30       # a fault must be detected within 30 days
RNG = np.random.default_rng(0)


def daily_resid(r: pd.DataFrame) -> pd.Series:
    return (r.y - r.pred).resample("D").mean()


def cusum_alarms(z: pd.Series, h: float) -> list:
    """Return dates of alarms; statistic resets after an alarm. NaN days are skipped."""
    s, out = 0.0, []
    for d, v in z.items():
        if np.isnan(v):
            continue
        s = max(0.0, s + v - K)
        if s > h:
            out.append(d); s = 0.0
    return out


def load_oof():
    res = {c: daily_resid(pd.read_parquet(ROOT / f"results/oof_{c}.parquet")) for c in COMPS}
    sig = {c: res[c].std() for c in COMPS}  # std, not MAD: residuals are heavy-tailed
    return res, sig


def false_alarm_rate(res, sig, h):
    days = set()
    for c in COMPS:
        days |= set(cusum_alarms(res[c] / sig[c], h))
    n_months = res[COMPS[0]].notna().sum() / 30.4
    return len(days) / n_months


def calibrate(res, sig):
    for h in np.arange(2.0, 30.0, 0.25):
        if false_alarm_rate(res, sig, h) <= FA_TARGET:
            return h
    raise RuntimeError("no threshold meets the false-alarm target")


def inject(res, comp, kind, amp_kw, t0):
    """Add a fault of amplitude amp_kw to component `comp` (and to the total) from day t0."""
    out = {c: s.copy() for c, s in res.items()}
    idx = out[comp].index
    days = (idx - t0).days.values.astype(float)
    if kind == "step":
        f = np.where(days >= 0, amp_kw, 0.0)
    else:  # ramp reaching amp_kw after 30 days
        f = np.clip(days / 30.0, 0, 1) * amp_kw
    out[comp] = out[comp] + f
    out["overhead_kw"] = out["overhead_kw"] + f
    return out


def first_detection(res, sig, h, t0):
    best = None
    for c in COMPS:
        z = res[c].loc[t0 - pd.Timedelta("30D"):t0 + pd.Timedelta(f"{HORIZON}D")] / sig[c]
        al = [d for d in cusum_alarms(z, h) if d >= t0]
        if al and (best is None or al[0] < best[0]):
            best = (al[0], c)
    return best


def main():
    res, sig = load_oof()
    h = calibrate(res, sig)
    fa = false_alarm_rate(res, sig, h)
    print("daily sigma (kW):", {c: round(s, 1) for c, s in sig.items()})
    print(f"threshold h={h:.2f}  ->  false alarms/month = {fa:.2f}")

    mean_overhead = 65.0  # kW, reference period mean
    idx = res["overhead_kw"].dropna().index
    starts = idx[(idx > idx[0] + pd.Timedelta("40D")) & (idx < idx[-1] - pd.Timedelta(f"{HORIZON}D"))][::7]
    rows = []
    for comp in ["hvac_kw", "pump_kw", "cooling_kw"]:
        for kind in ["step", "ramp"]:
            for pct in [0, 5, 10, 20, 30, 50, 100]:
                amp = pct / 100 * mean_overhead
                det, delays, right = 0, [], 0
                for t0 in starts:
                    r = first_detection(inject(res, comp, kind, amp, t0), sig, h, t0)
                    if r:
                        det += 1; delays.append((r[0] - t0).days); right += r[1] in (comp, "overhead_kw")
                rows.append(dict(component=comp, kind=kind, pct_overhead=pct, amp_kw=round(amp, 1),
                                 P_detect=det / len(starts),
                                 median_delay_d=np.median(delays) if delays else np.nan))
    t = pd.DataFrame(rows)
    t.to_csv(ROOT / "results/fault_validation.csv", index=False)
    print(f"{len(starts)} fault start dates per case")
    print(t.pivot_table(index=["component", "kind"], columns="pct_overhead", values="P_detect").round(2).to_string())
    print(t.pivot_table(index=["component", "kind"], columns="pct_overhead", values="median_delay_d").to_string())
    pd.Series({"h": h, "fa_per_month": fa, **{f"sigma_{c}": s for c, s in sig.items()}}).to_csv(ROOT / "results/detector_params.csv")


if __name__ == "__main__":
    main()
