"""[E] Convert the excess HVAC energy into EUR and tCO2, for the real site (Colorado)
and a 'what if the same data centre were in Grenoble' scenario.
All factors are 2024 values from primary sources (see FACTORS); ranges come from
(a) the excess-energy range across periods and (b) the price range where relevant.
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
USD_PER_EUR_2024 = 1.0824  # ECB reference rate, 2024 annual average (EXR.A.USD.EUR.SP00.A)

# excess HVAC energy, MWh/yr, from src/apply.py (results/week2_note.md)
EXCESS = {"central (12 months after step)": 1350, "low (2025 level)": 886, "high (2024 level)": 1486}

FACTORS = {
    "Golden, Colorado (real site)": dict(
        price_eur_kwh=(8.62 / 100 / USD_PER_EUR_2024, 11.71 / 100 / USD_PER_EUR_2024),
        price_src="EIA Electric Power Annual, Table 2.10, Colorado 2024: industrial 8.62 / commercial 11.71 ¢/kWh",
        co2_t_mwh=1036.6 * 0.45359237 / 1000,
        co2_src="EPA eGRID2023 (rev. 2), subregion RMPA, CO2 output rate 1,036.6 lb/MWh"),
    "Grenoble, France (what-if)": dict(
        price_eur_kwh=((0.1136 + 0.1066) / 2,) * 2,
        price_src="Eurostat nrg_pc_205, France, 20,000–69,999 MWh/yr (band IE, ESIF consumes ~25 GWh/yr), excl. VAT, 2024 S1/S2 average",
        co2_t_mwh=21.7 / 1000,
        co2_src="RTE Bilan électrique 2024, direct carbon intensity of French production, 21.7 gCO2eq/kWh"),
}


def main():
    rows = []
    for site, f in FACTORS.items():
        for case, mwh in EXCESS.items():
            rows.append(dict(site=site, case=case, MWh=mwh,
                             EUR_k_low=mwh * f["price_eur_kwh"][0], EUR_k_high=mwh * f["price_eur_kwh"][1],
                             tCO2=mwh * f["co2_t_mwh"]))
    t = pd.DataFrame(rows)
    t.round(1).to_csv(ROOT / "results/impact.csv", index=False)
    print(t.round(0).to_string(index=False))
    for s, f in FACTORS.items():
        print(f"\n{s}: price {f['price_eur_kwh'][0]:.4f}-{f['price_eur_kwh'][1]:.4f} EUR/kWh, CO2 {f['co2_t_mwh']:.4f} t/MWh")
        print("  ", f["price_src"]); print("  ", f["co2_src"])


if __name__ == "__main__":
    main()
