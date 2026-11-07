# Data Center Energy Health Check
*Every change in your energy overhead: detected, explained, priced.*

---

### The customer problem
- Since 2024, EU data centres with **≥ 500 kW of installed IT power** must report **PUE, WUE, ERF and REF** every year (Delegated Regulation (EU) 2024/1364). The Commission may follow with **minimum performance standards** (Directive (EU) 2023/1791, Art. 12).
- A yearly PUE says *how much* overhead a site has, but not ***what changed, when, and what it costs***.
- Overhead changes for good reasons (new equipment, new operating modes) and bad ones (faults, forgotten overrides, drifting controls). Both end up in the bill and in the reported KPIs; only a decision tells them apart.

### What the service does
| Step | What we do | Output |
|---|---|---|
| **1. Data & KPI baseline** | Map existing meters to the EU measurement points; compute PUE, ERF (plus WUE and REF where data exist) | EU-ready KPI sheet, data-gap list |
| **2. Expected-consumption model** | Learn how much each part of the plant *should* use for the current IT load, weather **and declared operating mode** | Expected vs measured, every day, per component |
| **3. Change detection, validated** | Flag undeclared deviations, attribute them to a component, and **publish the detector's limits** from synthetic-fault tests | Alarm log with component and size |
| **4. Price every change** | Turn each change into kWh, €, tCO₂ and PUE, with ranges and stated assumptions | A decision list: *intended? worth it? fix?* |
| *Continuous monitoring* | The operator declares mode changes; the model adapts in 4 weeks; anything undeclared raises an alarm | Monthly report / alerts |

### Demonstrated on a real site
Open data from the **NREL ESIF HPC data centre** (Golden, Colorado, USA; 10 years of 1-minute data), assessed *as if* it were subject to the EU rules.
- **[M]** PUE ≈ **1.03** for years, then **1.071 in 2024**. Almost all of the increase is HVAC: on **28 March 2024** it rose from ~12 kW to ~200 kW within two hours, with no change in IT load or weather, and stayed at 95–200 kW for the next 17 months.
- **[M]** The detector flagged it **the same day**, after four shorter episodes in the previous 13 months. These look like commissioning tests of a new operating mode, not a fault.
- **[E]** **The price of that change: ~1.35 GWh, €110–150k and ~635 tCO₂ a year** (overhead-based PUE 1.027 → 1.083). Is it intended, and is it worth it? The open data cannot say; the operator can. *What-if Grenoble:* the same change would cost ~€150k but emit only ~29 tCO₂.
- **[V]** Once the new mode is declared, the model learns it and stays quiet. It still finds a later **3 kW HVAC fault within ~6 days** (cooling and pump faults from 20–30 % of overhead), with about **one false alarm per quarter**. On the real data it then flagged **two smaller undeclared increases** (Dec 2024, Feb–Jun 2025).
- **[M]** **Data gap:** reused heat is no longer metered (ERF 0.13 → 0), although the EU rules require it.

### Next step: a physics-based digital twin
Calibrate a grey-box model of the plant (fans, pumps, heat exchangers) on the customer's design data and meters. It can **predict the cost of an operating mode before switching it on**, and set the expected baseline from day one instead of after 4 weeks of learning.

### Who it is for
Operators of enterprise, colocation and HPC data centres from **0.5 to 10 MW**, with meters in place but no dedicated energy-analytics staff.

---
*Methods, code and validation: [GitHub link]. Data: NREL ESIF PUE dataset, CC-BY, DOI 10.7799/3015212.*
