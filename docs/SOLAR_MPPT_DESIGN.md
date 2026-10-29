# Solar Energy Harvesting & MPPT Charge Controller Specification

## 1. Overview & Problem Statement

Field camera nodes deployed in agricultural environments operate without grid access and experience extreme weather variability (full equatorial sun, cloud cover, dust accumulation, partial crop foliage shading).

Standard linear charging ICs (such as the TP4056) suffer catastrophic efficiency collapse when paired with solar panels because they pull current until the solar panel voltage collapses to the battery voltage ($V_{\text{bat}} \approx 3.6\text{V} - 4.2\text{V}$), well below the panel's Maximum Power Point ($V_{\text{mp}} \approx 5.2\text{V} - 5.5\text{V}$). Under cloudy conditions, this collapse causes the charger to drop out entirely.

The **Proof-of-Weeding** edge node utilizes an active Maximum Power Point Tracking (MPPT) buck topology using the **Consonance CN3791**.

---

## 2. CN3791 Circuit Design & Dimensioning

```
 Solar Panel (+) ────┬────────────────────────────┐
 (6V Voc, 5.2V Vmp)  │                            │
                    [R1]                         [Cin] 10uF 25V X7R
                     │                            │
                     ├────────────▶ CN3791 (MPPT) │
                     │              Pin 8         │
                    [R2]                          │
                     │                            ▼
 Solar Panel (-) ────┴─────────────────────────── GND
```

### 2.1 MPPT Voltage Tracking Setpoint
The CN3791 monitors the input panel voltage via an internal 1.205V reference:
$$V_{\text{MPPT}} = 1.205\,\text{V} \times \left(1 + \frac{R_1}{R_2}\right)$$

For our target 6V / 3W monocrystalline solar cell with nominal maximum power point $V_{\text{mp}} = 5.20\,\text{V}$:
- Let $R_2 = 100.0\,\text{k}\Omega$ (1% tolerance, 0603)
- $R_1 = R_2 \times \left(\frac{5.20}{1.205} - 1\right) = 100 \times 3.315 = 331.5\,\text{k}\Omega$
- Select standard EIA E96 1% value: **$R_1 = 330\,\text{k}\Omega$** (yields $V_{\text{MPPT}} = 5.18\,\text{V}$, within 0.4% of optimum).

### 2.2 Charge Current Regulation ($I_{\text{CHG}}$)
Charge current is programmed by external high-side current sensing resistor $R_{\text{CS}}$:
$$I_{\text{CHG}} = \frac{120\,\text{mV}}{R_{\text{CS}}}$$

- For our 3200 mAh 18650 cell, target charge rate is $C/3.2 \approx 1.0\,\text{A}$:
  $$R_{\text{CS}} = \frac{0.120\,\text{V}}{1.0\,\text{A}} = 0.120\,\Omega = 120\,\text{m}\Omega$$
- Selected component: **$120\,\text{m}\Omega$, 1%, 0.5W, 1206 package**.

### 2.3 Buck Inductor Selection
- Inductance: **$10\,\mu\text{H}$**
- Saturation Current ($I_{\text{sat}}$): $> 2.4\,\text{A}$ (e.g., Bourns SRR1260-100M).
- DC Resistance (DCR): $< 35\,\text{m}\Omega$ for minimal conduction losses.

---

## 3. Battery Chemistry & Safety System

| Parameter | LiFePO4 (Recommended) | Li-ion 18650 (Standard) |
| :--- | :--- | :--- |
| **Nominal Voltage** | 3.2 V | 3.7 V |
| **Float / Full Charge** | 3.65 V | 4.20 V |
| **Brownout Cutoff** | 2.80 V | 3.30 V |
| **Thermal Operating Window**| -20°C to +65°C | 0°C to +45°C (charge) |
| **Cycle Life (80% DoD)** | > 2000 cycles | ~ 500 cycles |

### 3.1 NTC Thermistor Temperature Monitoring
The CN3791 pin 7 (TEMP) monitors an external 10k NTC thermistor ($\beta = 3950$) thermally bonded to the battery casing:
- Cold cutoff: Suspends charging if cell temperature drops below 0°C (prevents lithium plating).
- Hot cutoff: Suspends charging if cell temperature exceeds 45°C (prevents thermal runaway in direct sunlight).

---

## 4. Efficiency Benchmarks (Synthetic vs Linear Baseline)

| Condition | Solar Irradiance | Linear (TP4056) Power Harvest | CN3791 MPPT Power Harvest | Net Harvest Gain |
| :--- | :--- | :--- | :--- | :--- |
| **Full Sun** | $1000\,\text{W/m}^2$ | 1.82 W | 2.76 W | **+51.6%** |
| **Overcast Sky**| $250\,\text{W/m}^2$ | 0.28 W | 0.61 W | **+117.8%** |
| **Heavy Shade** | $80\,\text{W/m}^2$ | 0.00 W (dropout) | 0.18 W | **Inf (operational)**|
