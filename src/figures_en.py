"""English figures for the recruiter-facing documents (docs/fig_*.png)."""
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

ROOT = Path(__file__).resolve().parents[1]
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})


def fig_kpi():
    k = pd.read_csv(ROOT / "results/kpi_annual.csv", index_col=0)
    k = k[~k.partial_year]
    oh = k[["cooling_MWh", "hvac_MWh", "pump_MWh", "plug_and_light_MWh"]].div(k.E_IT_MWh, axis=0) * 100
    fig, ax = plt.subplots(figsize=(7.5, 3.0))
    bottom = 0
    for c, lab, col in zip(oh.columns, ["Cooling (outdoor)", "HVAC (air side)", "Pumps", "Lights & plugs"],
                           ["#4C78A8", "#E45756", "#72B7B2", "#BAB0AC"]):
        ax.bar(oh.index, oh[c], bottom=bottom, label=lab, color=col, width=.7)
        bottom = bottom + oh[c]
    for x, (tot, pue) in enumerate(zip(bottom, k.PUE)):
        ax.text(oh.index[x], tot + .15, f"PUE\n{pue:.3f}", ha="center", fontsize=8)
    ax.set_ylabel("Overhead, % of IT energy"); ax.set_ylim(0, 8.6)
    ax.set_title("Annual overhead by component (complete years)", loc="left")
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    fig.tight_layout(); fig.savefig(ROOT / "docs/fig_kpi.png", dpi=200)


def fig_hvac():
    d = pd.read_parquet(ROOT / "results/hvac_daily.parquet")
    ep = pd.read_csv(ROOT / "results/alarm_episodes.csv", parse_dates=["first_alarm"])
    fig, ax = plt.subplots(figsize=(7.5, 3.3))
    ax.fill_between(d.index, d.pred, d.y, where=d.y > d.pred, color="#E45756", alpha=.25, lw=0,
                    label="Excess (measured − expected)")
    ax.plot(d.index, d.y, color="#E45756", lw=1, label="Measured")
    ax.plot(d.index, d.pred, color="k", lw=1, label="Expected (model: IT load + weather)")
    f = ep[ep.component == "hvac_kw"].first_alarm
    ax.plot(f, [195] * len(f), "v", color="#F58518", ms=6, label="Alarm raised")
    ax.annotate("28 Mar 2024\nstep, flagged\nsame day", xy=(pd.Timestamp("2024-03-28"), 150),
                xytext=(pd.Timestamp("2023-06-01"), 120), fontsize=8, arrowprops=dict(arrowstyle="->", lw=.8))
    ax.annotate("Earlier\nepisodes", xy=(pd.Timestamp("2023-03-30"), 35),
                xytext=(pd.Timestamp("2022-10-01"), 60), fontsize=8, arrowprops=dict(arrowstyle="->", lw=.8))
    ax.set_ylim(0, 210); ax.set_ylabel("HVAC power, kW (daily mean)")
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.set_title("HVAC power: measured vs expected", loc="left", pad=24)
    ax.legend(frameon=False, fontsize=8, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=4,
              handlelength=1.5, columnspacing=1.0)
    fig.tight_layout(); fig.savefig(ROOT / "docs/fig_hvac.png", dpi=200)


def fig_simple():
    """Minimal chart for the one-page offer sheet: expected vs measured, one annotation."""
    d = pd.read_parquet(ROOT / "results/hvac_daily.parquet").loc["2023-07-01":"2024-12-31"]
    fig, ax = plt.subplots(figsize=(6.4, 2.2))
    ax.plot(d.index, d.pred, color="#0b3d2e", lw=2, label="Normal (expected)")
    ax.plot(d.index, d.y, color="#E45756", lw=2, label="Actual")
    ax.annotate("+190 kW in one evening\nspotted the same day", xy=(pd.Timestamp("2024-03-29"), 120),
                xytext=(pd.Timestamp("2023-07-20"), 120), fontsize=10.5, va="center",
                arrowprops=dict(arrowstyle="->", lw=1.2))
    ax.set_ylabel("Power, kW", fontsize=10)
    ax.tick_params(labelsize=9.5)
    ax.set_ylim(0, 220)
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.legend(frameon=False, fontsize=10, loc="upper left", bbox_to_anchor=(0, 1.2), ncol=2)
    fig.tight_layout(); fig.savefig(ROOT / "docs/fig_simple.png", dpi=220)


if __name__ == "__main__":
    fig_kpi(); fig_hvac(); fig_simple()
