"""Exploration figures (figures/01, 02): monthly overhead vs IT load, and the HVAC step."""
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
COMP = ["cooling_kw", "hvac_kw", "pump_kw", "plug_and_light_kw"]


def main():
    h = pd.read_parquet(ROOT / "data/processed/hourly_clean.parquet")
    m = h["2016-06":"2025-08"].resample("MS")[["it_power_kw", *COMP]].mean()
    fig, ax = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
    m[COMP].rename(columns=lambda c: c.replace("_kw", "")).plot.area(ax=ax[0], lw=0)
    ax[0].set_ylabel("overhead kW (monthly mean)")
    ax[0].set_title("ESIF: overhead components vs IT load")
    m.it_power_kw.plot(ax=ax[1], color="k"); ax[1].set_ylabel("IT kW")
    fig.tight_layout(); fig.savefig(ROOT / "figures/01_overhead_monthly.png", dpi=130)

    s = h["2024-03-20":"2024-04-06"]
    fig, ax = plt.subplots(figsize=(11, 3.5)); a2 = ax.twinx()
    ax.plot(s.index, s.hvac_kw, "C3"); a2.plot(s.index, s.it_power_kw, "k", alpha=.4)
    ax.set_ylabel("HVAC kW", color="C3"); a2.set_ylabel("IT kW")
    ax.set_title("HVAC step on 28 Mar 2024, 20:00 (IT load and weather unchanged)")
    fig.tight_layout(); fig.savefig(ROOT / "figures/02_hvac_step.png", dpi=130)


if __name__ == "__main__":
    main()
