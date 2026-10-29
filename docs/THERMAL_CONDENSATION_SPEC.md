# Thermal & Condensation Engineering Specification

## 1. Thermodynamic Field Problem Analysis

Sealed outdoor electronic enclosures in agricultural settings suffer severe diurnal temperature cycling:
- **Solar Noon Heating:** Internal air temperature can reach $+65^\circ\text{C}$, causing internal air expansion and positive gauge pressure ($\Delta P \approx +15\,\text{kPa}$).
- **Rapid Dusk Cooling:** Ambient temperature drops rapidly towards dew point ($+10^\circ\text{C}$ to $+15^\circ\text{C}$), generating strong negative gauge pressure ($\Delta P \approx -12\,\text{kPa}$) that attempts to suck ambient moist air past perimeter seals.
- **Internal Condensation:** When humid air is trapped inside a sealed housing, cooling causes moisture to condense directly onto the coolest surface: the exposed optical borosilicate glass lens port. Fogged glass distorts the ExG green vegetation index, causing false-positive or false-negative analysis rejections.

---

## 2. Mitigation Architecture

```
     External Air (Variable RH, Rain, Dust)
                    │
                    ▼
   +------------------------------------+
   |  ePTFE Vent (Gore PMF100318)       |
   |  - Microporous Membrane (0.2 µm)   | <--- Equalizes pressure; blocks liquid water & dust
   +----------------+-------------------+
                    │ Dry Air Exchange
                    ▼
   +------------------------------------+
   |  Internal Sealed Chamber           |
   |                                    |
   |   [Desiccant Pocket (5g Silica)]   | <--- Traps residual moisture (RH < 20%)
   |                                    |
   |        [Camera Sensor & Lens]      |
   |                  │                 |
   |                  ▼                 |
   |       [Borosilicate Window]        | <--- Glass temperature stays above internal dew point
   +------------------------------------+
```

---

## 3. Component Dimensioning & Parameters

### 3.1 ePTFE Pressure Equalization Membrane (Gore Vent)
- **Model:** W.L. Gore Snap-in Vent PMF100318 or M12 Screw-in Vent (IP67/IP68).
- **Pore Size:** $0.2\,\mu\text{m}$ average pore diameter (10,000 times smaller than a water droplet, 700 times larger than a water vapor molecule).
- **Water Entry Pressure (WEP):** $> 60\,\text{kPa}$ ($> 6.0\,\text{m}$ water column equivalent, vastly exceeding IP67 requirement of $1.0\,\text{m}$).
- **Airflow Rate:** $\ge 300\,\text{ml/min/cm}^2$ at $\Delta P = 70\,\text{mbar}$, preventing seal stress during abrupt thermal transitions.

### 3.2 Desiccant Absorption System
- **Composition:** 5-gram sachet of non-indicating Type A Silica Gel or 4A Molecular Sieve.
- **Retention Pocket:** Integrated injection-molded snap-in retention bay positioned adjacent to the camera sensor flex cable.
- **Moisture Capacity:** $1.6\,\text{g}$ $H_2O$ absorption at $25^\circ\text{C}$ / $80\%$ RH ($> 32\%$ by dry weight).
- **Dew Point Target:** With an initial internal chamber volume of $180\,\text{cm}^3$, the desiccant reduces steady-state internal relative humidity to $< 20\%$, suppressing the internal dew point to below $-8^\circ\text{C}$. This guarantees zero glass condensation across all terrestrial operating environments.

---

## 4. Optical Quality Gate Integration

In addition to physical prevention, Attester A (Python) and Attester B (Rust) execute an environmental quality gate prior to running the ExG vegetation pipeline:
- **Laplacian Focus Variance Gate:** Measures edge sharpness across the frame ($\sigma^2_{\text{Laplacian}} > 100$). Condensation fogging produces severe high-frequency attenuation ($\sigma^2 < 45$), triggering immediate `ERR_CONDENSATION_FOG` rejection without recording faulty on-chain evidence.
