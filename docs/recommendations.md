# Recommendations
Ranked by value ÷ effort. Labels: [M] measured · [V] validated · [E] estimated.

### 1. Explain the change (cost: one site visit or a BMS log review)
- **Finding [M]:** on 28 Mar 2024, 20:00, HVAC rose from ~12 kW to ~200 kW within two hours, with no change in IT load or weather, and stayed at 95–200 kW for 17 months in clean steps. Four shorter episodes in the 13 months before look like commissioning tests.
- **Most likely:** a deliberate new operating mode, or a change in what the HVAC meter covers. A fault going unnoticed for 17 months is the least likely explanation.
- **Action:** check the HVAC meter scope and the controls change log for the fan walls, electrical-room fan coils and make-up air unit on those dates.

### 2. Decide with the price on the table (~1.35 GWh, €110–150k, 635 tCO₂ a year [E])
- If the mode is needed: declare it, so the monitor learns the new level (4-week window) and watches for faults on top of it.
- If it is not needed: restoring the previous operation is worth ~1.35 GWh a year; every 10 kW of HVAC is ~88 MWh a year.
- In France the same change would cost ~€150k but emit only ~29 tCO₂: the argument is cost and EU compliance.

### 3. Close the data gaps (cost: low)
- **Heat reuse [M]:** ERF falls from 0.13 (2017) to 0 (2024) while heat reuse is still active: restore E_REUSE metering (required by the EU rules).
- **Operating-mode log:** record mode changes and running pumps, so the monitor can tell intended changes from faults. [V] With declared modes it found a 3 kW HVAC fault within ~6 days and raised no alarm on the declared change.
