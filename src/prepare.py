"""Minute data ESIF -> clean hourly dataset (data/processed/hourly_clean.parquet).

Cleaning rules (logged in the 'flag_*' columns, never silently dropped):
- coverage: an hour is valid only if it has >= 30 one-minute samples
- IT power < 100 kW -> invalid (outages, maintenance)
- PUE outside [1.0, 1.5] -> invalid (metering glitches)
- negative component powers -> invalid
- outside air: drop the 1970 placeholder row, keep -40..50 degC
"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data/raw", ROOT / "data/processed"
COMP = ["cooling_kw", "hvac_kw", "pump_kw", "plug_and_light_kw"]


def main():
    p = pd.read_parquet(RAW / "pue.parquet", columns=["ts", "it_power_kw", *COMP, "pue", "ere"])
    p = p.set_index("ts").sort_index()
    o = pd.read_parquet(RAW / "outside.parquet", columns=["ts", "outdoor_air_temp", "outdoor_air_humidity"])
    o = o[o.ts > "2000"].set_index("ts").sort_index()

    h = p.resample("1h").mean()
    h["n_samples"] = p.it_power_kw.resample("1h").count()
    w = o.resample("1h").mean()
    w["T_C"] = (w.outdoor_air_temp - 32) * 5 / 9
    w["RH"] = w.outdoor_air_humidity
    w.loc[~w.T_C.between(-40, 50), ["T_C", "RH"]] = np.nan
    h = h.join(w[["T_C", "RH"]], how="left")

    h["overhead_kw"] = h[COMP].sum(axis=1, min_count=len(COMP))
    h["total_kw"] = h.it_power_kw + h.overhead_kw
    h["pue_calc"] = h.total_kw / h.it_power_kw

    h["flag_coverage"] = h.n_samples < 30
    h["flag_it_low"] = h.it_power_kw < 100
    h["flag_pue"] = ~h.pue_calc.between(1.0, 1.5)
    h["flag_negative"] = (h[COMP] < 0).any(axis=1)
    flags = [c for c in h if c.startswith("flag_")]
    h["valid"] = ~h[flags].any(axis=1)

    OUT.mkdir(parents=True, exist_ok=True)
    h.to_parquet(OUT / "hourly_clean.parquet")
    print(f"hours: {len(h)}, valid: {h.valid.sum()} ({h.valid.mean():.1%})")
    print(h[flags].sum().to_string())


if __name__ == "__main__":
    main()
