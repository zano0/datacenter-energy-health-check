"""Regime-aware baseline: operating-mode changes declared by the operator are treated as
known inputs, not as anomalies.

After a declared change the reference model (which knows IT load and weather) is kept, and
a per-component offset is learned over a LEARN-day commissioning window (median daily
residual). During the window no alarms are raised. Afterwards the detector watches the
residual against the shifted baseline, with the threshold and sigmas validated on the
reference period.

REGIME_LOG is ILLUSTRATIVE: ESIF publishes no operator log. Only two changes are declared,
so that later level changes stay undeclared and test the detector.

Validation: on clean out-of-fold data, declare a +100 kW HVAC change at a random date,
learn the offset, then inject an undeclared fault 28 days later. Measure (a) alarms caused
by the declared change itself and (b) detection of the later fault.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import detector as D

ROOT = Path(__file__).resolve().parents[1]
LEARN = int(__import__("os").environ.get("LEARN", 28))  # days of commissioning window after a declared change
AFFECTED = ["hvac_kw", "overhead_kw"]  # an HVAC mode change shifts HVAC and the total
REGIME_LOG = [  # (start, description, affected components) — illustrative operator log
    ("2024-03-28 20:00", "Mode B: new HVAC operating mode (~190 kW)", AFFECTED),
    ("2025-01-01 00:00", "Mode C: reduced HVAC operating mode (~110 kW)", AFFECTED),
]


def regime_residuals(res: dict, log) -> tuple[dict, pd.Series]:
    """Shift each component's daily residual by the offset learned after each declared change.
    Returns adjusted residuals and a boolean Series of 'learning' days (alarms suppressed)."""
    idx = res[D.COMPS[0]].index
    learning = pd.Series(False, index=idx)
    out = {c: s.copy() for c, s in res.items()}
    starts = [pd.Timestamp(e[0]).normalize() for e in log]
    for i, (t0, (_, _, comps)) in enumerate(zip(starts, log)):
        t_end = starts[i + 1] if i + 1 < len(starts) else idx[-1] + pd.Timedelta("1D")
        win = (idx >= t0) & (idx < t0 + pd.Timedelta(f"{LEARN}D"))
        seg = (idx >= t0) & (idx < t_end)
        learning |= pd.Series(win, index=idx)
        for c in comps:
            off = res[c][win].median()
            out[c][seg] = res[c][seg] - off
    return out, learning


def run_detector(res, sig, h, learning):
    alarms = []
    for c in D.COMPS:
        z = res[c] / sig[c]
        z[learning] = np.nan  # no monitoring during commissioning; CUSUM restarts afterwards
        z = z.copy()
        s, prev_nan = 0.0, False
        for d, v in z.items():
            if np.isnan(v):
                prev_nan = prev_nan or bool(learning.get(d, False))
                continue
            if prev_nan:
                s, prev_nan = 0.0, False
            s = max(0.0, s + v - D.K)
            if s > h:
                alarms.append((d, c)); s = 0.0
    return pd.DataFrame(alarms, columns=["date", "component"]).sort_values("date")


def episodes(al):
    eps = []
    for c, g in al.groupby("component"):
        new = g.date.diff().dt.days.fillna(99) > 3
        for _, s in g.groupby(new.cumsum()):
            eps.append(dict(component=c, first_alarm=s.date.min().date(), last_alarm=s.date.max().date(),
                            n_alarms=len(s)))
    return pd.DataFrame(eps).sort_values("first_alarm") if eps else pd.DataFrame()


def validate(res, sig, h):
    mean_overhead = 65.0
    idx = res["overhead_kw"].dropna().index
    starts = idx[(idx > idx[0] + pd.Timedelta("40D")) & (idx < idx[-1] - pd.Timedelta("60D"))][::7]
    rows = []
    for comp in ["hvac_kw", "pump_kw", "cooling_kw"]:
        for pct in [0, 5, 10, 20, 30, 50]:
            amp = pct / 100 * mean_overhead
            n_ref_alarm, n_aware_alarm_declared, det, delays = 0, 0, 0, []
            for t0 in starts:
                r = D.inject(res, "hvac_kw", "step", 100.0, t0)          # declared +100 kW change
                tf = t0 + pd.Timedelta("28D")
                if pct:
                    r = D.inject(r, comp, "step", amp, tf)               # undeclared fault later
                win = {c: s.loc[t0 - pd.Timedelta("30D"):tf + pd.Timedelta(f"{D.HORIZON}D")] for c, s in r.items()}
                # reference-only detector: does the declared change itself raise an alarm?
                if pct == 0:
                    n_ref_alarm += D.first_detection(win, sig, h, t0) is not None
                adj, learning = regime_residuals(win, [(t0, "declared", AFFECTED)])
                al = run_detector(adj, sig, h, learning)
                before = al[(al.date >= t0) & (al.date < tf)]
                n_aware_alarm_declared += len(before) > 0
                after = al[al.date >= tf]
                if len(after):
                    det += 1; delays.append((after.date.min() - tf).days)
            n = len(starts)
            rows.append(dict(fault_component=comp, pct_overhead=pct, amp_kw=round(amp, 1),
                             alarm_on_declared_change_reference_only=(n_ref_alarm / n) if pct == 0 else np.nan,
                             alarm_on_declared_change_regime_aware=n_aware_alarm_declared / n,
                             P_detect_later_fault=det / n,
                             median_delay_d=np.median(delays) if delays else np.nan))
    return pd.DataFrame(rows)


def main():
    p = pd.read_csv(ROOT / "results/detector_params.csv", index_col=0).iloc[:, 0]
    h = p["h"]; sig = {c: p[f"sigma_{c}"] for c in D.COMPS}

    # --- validation on clean out-of-fold data
    res_oof, _ = D.load_oof()
    v = validate(res_oof, sig, h)
    v.to_csv(ROOT / "results/regime_validation.csv", index=False)
    print(v.round(2).to_string(index=False))

    # --- real data, declared log
    import baseline as B
    import apply as A
    hh, X = B.load()
    ex = {c: A.expected(hh, X, c) for c in D.COMPS}
    res = {c: D.daily_resid(ex[c]) for c in D.COMPS}
    adj, learning = regime_residuals(res, REGIME_LOG)
    ep = episodes(run_detector(adj, sig, h, learning))
    ep = ep[pd.to_datetime(ep.first_alarm) >= pd.Timestamp(REGIME_LOG[0][0]).normalize()]
    ep.to_csv(ROOT / "results/regime_alarm_episodes.csv", index=False)
    print("\nAlarms after the first declared change (regime-aware):")
    print(ep.to_string(index=False))

    # --- figure: HVAC measured vs regime-aware expected
    d = pd.DataFrame({"y": ex["hvac_kw"].y.resample("D").mean(), "ref": ex["hvac_kw"].pred.resample("D").mean()})
    d["aware"] = d.y - adj["hvac_kw"]
    d = d.loc["2023-10-01":]
    fig, ax = plt.subplots(figsize=(7.5, 3.3))
    ax.plot(d.index, d.y, color="#E45756", lw=1, label="Measured")
    ax.plot(d.index, d.ref, color="#999", lw=1, ls="--", label="Expected, reference only")
    ax.plot(d.index, d.aware, color="k", lw=1, label="Expected, regime-aware")
    for t, desc, _ in REGIME_LOG:
        t = pd.Timestamp(t)
        ax.axvspan(t, t + pd.Timedelta(f"{LEARN}D"), color="#4C78A8", alpha=.15, lw=0)
        ax.text(t, 215, desc.split(":")[0] + " declared", fontsize=7, color="#4C78A8")
    f = pd.to_datetime(ep[ep.component == "hvac_kw"].first_alarm)
    ax.plot(f, [205] * len(f), "v", color="#F58518", ms=6, label="Alarm (undeclared change)")
    ax.set_ylim(0, 230); ax.set_ylabel("HVAC power, kW (daily mean)")
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.set_title("Regime-aware baseline: declared changes are learned, undeclared ones are flagged", loc="left",
                 pad=24, fontsize=10)
    ax.legend(frameon=False, fontsize=7.5, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=4)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    fig.tight_layout(); fig.savefig(ROOT / "docs/fig_regimes.png", dpi=200)


if __name__ == "__main__":
    main()
