"""Annual EED-style KPIs for ESIF, computed as if the site were in scope of
Delegated Regulation (EU) 2024/1364 (Annex III). All values are [M] measured.

- PUE  = E_DC / E_IT  (energy ratio over the year, not the mean of hourly PUE)
- ERF  = E_REUSE / E_DC, with E_REUSE derived from the dataset's ERE:
         ERE = (E_DC - E_REUSE) / E_IT  ->  E_REUSE = (PUE - ERE) * E_IT
- CDD  = cooling degree days, Eurostat method: day counts (Tm - 21) if Tm >= 24 degC
- WUE, REF: not available in the open data
Only valid hours are used; coverage is reported for transparency.
"""
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
COMP = ["cooling_kw", "hvac_kw", "pump_kw", "plug_and_light_kw"]


def main():
    h = pd.read_parquet(ROOT / "data/processed/hourly_clean.parquet")
    v = h[h.valid].copy()
    v["reuse_kw"] = ((v.pue - v.ere) * v.it_power_kw).clip(lower=0)

    y = v.groupby(v.index.year)
    k = pd.DataFrame({
        "coverage_%": 100 * y.size() / h.groupby(h.index.year).size(),
        "E_IT_MWh": y.it_power_kw.sum() / 1e3,
        "E_DC_MWh": y.total_kw.sum() / 1e3,
    })
    for c in COMP:
        k[f"{c.replace('_kw', '')}_MWh"] = y[c].sum() / 1e3
    k["PUE"] = k.E_DC_MWh / k.E_IT_MWh
    k["ERF"] = y.reuse_kw.sum() / 1e3 / k.E_DC_MWh
    tm = h.T_C.resample("D").mean()
    cdd = (tm - 21).where(tm >= 24, 0)
    k["CDD"] = cdd.groupby(cdd.index.year).sum()
    k["weather_days"] = tm.notna().groupby(tm.index.year).sum()
    k["partial_year"] = [yr in (2015, 2016, 2025) for yr in k.index]
    k = k.drop(index=2015, errors="ignore")

    out = ROOT / "results"
    k.round(4).to_csv(out / "kpi_annual.csv")
    print(k.round(3).to_string())

    fig, ax = plt.subplots(1, 2, figsize=(11, 3.8))
    ax[0].bar(k.index, k.PUE, color=["#bbb" if p else "C0" for p in k.partial_year])
    ax[0].set_ylim(1.0, 1.1); ax[0].set_title("Annual PUE (E_DC/E_IT) · grey = partial year")
    oh = k[[f"{c.replace('_kw', '')}_MWh" for c in COMP]].div(k.E_IT_MWh, axis=0) * 100
    oh.columns = ["cooling", "HVAC", "pumps", "plug & light"]
    oh.plot.bar(stacked=True, ax=ax[1], rot=0); ax[1].set_title("Overhead, % of IT energy")
    fig.tight_layout(); fig.savefig(ROOT / "figures/03_kpi_annual.png", dpi=130)


if __name__ == "__main__":
    main()
