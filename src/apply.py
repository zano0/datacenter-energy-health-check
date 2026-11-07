"""Run the validated detector on the real ESIF data (2022-07 .. 2025-08).

Expected values: out-of-fold predictions inside the reference period, predictions of the
model trained on the full reference period everywhere else (incl. known events, which
were excluded from training). Outputs alarm list and excess-energy estimate.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import baseline as B
import detector as D

ROOT = Path(__file__).resolve().parents[1]
START, END = "2022-07-01", "2025-08-31"


def expected(h, X, target):
    v = h.loc[START:END]
    v = v[v.valid]
    pred = pd.Series(B.fit_reference(h, X, target).predict(X.loc[v.index]), index=v.index)
    oof = pd.read_parquet(ROOT / f"results/oof_{target}.parquet")
    pred.loc[oof.index] = oof.pred
    return pd.DataFrame({"y": v[target], "pred": pred})


def main():
    h, X = B.load()
    p = pd.read_csv(ROOT / "results/detector_params.csv", index_col=0).iloc[:, 0]
    hthr = p["h"]
    ex = {c: expected(h, X, c) for c in D.COMPS}
    alarms = []
    for c in D.COMPS:
        z = D.daily_resid(ex[c]) / p[f"sigma_{c}"]
        alarms += [(d, c) for d in D.cusum_alarms(z, hthr)]
    al = pd.DataFrame(alarms, columns=["date", "component"]).sort_values("date")
    al.to_csv(ROOT / "results/alarms_real.csv", index=False)
    # merge alarms of the same component less than 4 days apart into episodes
    eps = []
    for c, g in al.groupby("component"):
        new = g.date.diff().dt.days.fillna(99) > 3
        for _, s in g.groupby(new.cumsum()):
            eps.append(dict(component=c, first_alarm=s.date.min().date(), last_alarm=s.date.max().date(), n_alarms=len(s)))
    ep = pd.DataFrame(eps).sort_values("first_alarm")
    ep.to_csv(ROOT / "results/alarm_episodes.csv", index=False)
    print(ep.to_string(index=False))

    # excess HVAC energy after the step: actual - expected, first 12 months
    e = ex["hvac_kw"]
    for a, b, lab in [("2024-03-28 20:00", "2025-03-28 19:00", "12 months after the step"),
                      ("2024-03-28 20:00", "2024-12-31 23:00", "2024 after the step"),
                      ("2025-01-01", "2025-08-31 23:00", "2025 (Jan-Aug)")]:
        s = e.loc[a:b]
        exc = (s.y - s.pred)
        cov = len(s) / (len(pd.date_range(a, b, freq="h")))
        print(f"{lab}: mean excess HVAC {exc.mean():.1f} kW, expected {s.pred.mean():.1f} kW, "
              f"actual {s.y.mean():.1f} kW, coverage {cov:.0%}, annualized {exc.mean()*8760/1e3:.0f} MWh/yr")
    # uncertainty of the expected value: spread of monthly-mean OOF residuals
    oof = pd.read_parquet(ROOT / "results/oof_hvac_kw.parquet")
    print("sd of monthly-mean HVAC residual (OOF):", round((oof.y - oof.pred).resample("MS").mean().std(), 2), "kW")
    o = ex["overhead_kw"].loc["2024-03-28 20:00":"2025-03-28 19:00"]
    print(f"total overhead, 12 months: actual {o.y.mean():.1f} kW vs expected {o.pred.mean():.1f} kW")
    it = h.it_power_kw.loc["2024-03-28 20:00":"2025-03-28 19:00"].mean()
    print(f"mean IT {it:.0f} kW -> overhead-based PUE actual {1+o.y.mean()/it:.3f} vs expected {1+o.pred.mean()/it:.3f}")

    # figure: daily HVAC actual vs expected, excess shaded, first alarm of each HVAC episode
    d = {k: v.resample("D").mean() for k, v in ex["hvac_kw"].items()}
    pd.DataFrame(d).to_parquet(ROOT / "results/hvac_daily.parquet")
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.fill_between(d["y"].index, d["pred"], d["y"], where=d["y"] > d["pred"], color="C3", alpha=.25,
                    lw=0, label="excess (measured − expected)")
    ax.plot(d["y"].index, d["y"], color="C3", lw=1, label="HVAC measured")
    ax.plot(d["pred"].index, d["pred"], color="k", lw=1, label="HVAC expected (model)")
    first = ep[ep.component == "hvac_kw"].first_alarm
    ax.plot(pd.to_datetime(first), [190] * len(first), "v", color="C1", ms=8, label="first alarm of an episode")
    ax.set_ylim(0, 210); ax.set_ylabel("kW (daily mean)")
    ax.set_title("ESIF – HVAC power: measured vs expected from IT load and weather")
    ax.legend(loc="upper left", fontsize=8); fig.tight_layout()
    fig.savefig(ROOT / "figures/04_hvac_expected_vs_measured.png", dpi=130)

if __name__ == "__main__":
    main()
