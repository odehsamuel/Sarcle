# Vegetation & Soil Metrics Specification

This specification defines the registry of quantifiable surface metrics supported by Proof-of-Weeding. Every metric is assigned an integer `metric_id` (`u32`).

---

## 1. Metric Units & Representation

All metric outputs reported to `evidence_registry` are expressed in **basis points (bps)**, represented as an unsigned integer `u32` bounded between $0$ and $10,000$:
* $0\text{ bps} = 0.00\%$
* $500\text{ bps} = 5.00\%$
* $2,500\text{ bps} = 25.00\%$
* $10,000\text{ bps} = 100.00\%$

Values $> 10,000$ are rejected by the smart contract.

---

## 2. Metric Registry

| Metric ID | Identifier | Status | Primary Application |
| :--- | :--- | :--- | :--- |
| **`1`** | `green_cover_exg` | **Implemented** | Excess Green index vegetation cover fraction |
| **`2`** | `bare_soil_fraction` | *Specified Stub* | Direct soil exposure index via red chromaticity |
| **`3`** | `canopy_gap_fraction` | *Specified Stub* | Spatial vegetation fragmentation & weed patchiness |

---

## 3. Metric 1: `green_cover_exg` (Implemented)

### 3.1 Overview
Measures the proportion of green vegetation pixels relative to total pixels within the active region of interest (ROI) using the classical Excess Green ($\text{ExG}$) chromaticity index.

### 3.2 Mathematical Formulation
1. Let $(R, G, B)$ be the 8-bit color channels of an sRGB pixel inside the polygon ROI.
2. Compute normalized chromaticity coordinates:
   $$r = \frac{R}{R + G + B + \epsilon}, \quad g = \frac{G}{R + G + B + \epsilon}, \quad b = \frac{B}{R + G + B + \epsilon}$$
   (where $\epsilon = 10^{-6}$ avoids division by zero in shadow pixels).
3. Compute Excess Green:
   $$\text{ExG} = 2g - r - b$$
4. Apply an adaptive Otsu threshold $T_{\text{otsu}}$ clamped to the pre-configured range $[T_{\min}, T_{\max}]$:
   $$\text{Mask}(x,y) = \begin{cases} 1 & \text{if } \text{ExG}(x,y) > T_{\text{clamped}} \\ 0 & \text{otherwise} \end{cases}$$
5. Apply morphological opening ($3 \times 3$ ellipse structuring element) to remove high-frequency sensor noise.
6. Compute output in basis points:
   $$\text{cover\_bps} = \text{round}\left( \frac{\sum_{(x,y) \in \text{ROI}} \text{Mask}(x,y)}{\text{Count}(\text{ROI})} \times 10000 \right)$$

### 3.3 Determinism Requirements
- All parameters (color balance mode, Otsu clamping limits, morphological kernel size) must be codified in the analyzer configuration.
- $\text{analyzer\_hash} = \text{SHA-256}(\text{Canonical-JSON}(\{\text{algorithm\_id}, \text{version}, \text{params}\}))$.

---

## 4. Metric 2: `bare_soil_fraction` (Specified Stub)

### 4.1 Overview
Measures the fraction of uncovered bare mineral soil or dried substrate within the ROI. Useful for verifying that rocky paths or gravel firebreaks are completely barren.

### 4.2 Proposed Algorithm Specification
* **Inputs**: RGB JPEG frame, canonical ROI polygon.
* **Method**: Normalized Difference Soil Index ($\text{NDSI}$) approximation using Red-Green chromaticity ratio:
  $$\text{SoilIndex} = \frac{R - G}{R + G + \epsilon}$$
  Coupled with a minimum luminance threshold to reject dark organic mulch or wet soil depressions.
* **Output**: Basis points ($0-10000$), where $10000$ represents 100% exposed mineral soil.
* **Determinism**: Requires fixed-point channel conversion and pinned chromaticity thresholds.

---

## 5. Metric 3: `canopy_gap_fraction` (Specified Stub)

### 5.1 Overview
Measures the spatial dispersion and continuity of vegetation gaps. Useful for pasture weeding where isolated grass clumps are permitted, but contiguous weed carpets are prohibited.

### 5.2 Proposed Algorithm Specification
* **Inputs**: Binary vegetation mask generated from Metric 1, canonical ROI polygon.
* **Method**: Connected component analysis and distance transform to compute average distance from non-vegetated soil to the nearest green pixel.
* **Output**: Basis points ($0-10000$) mapping normalized mean gap radius to maximum permissible clearing span.
* **Determinism**: Requires integer-grid 8-connectivity labeling and fixed spatial resolution resampling.
