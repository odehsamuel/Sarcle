# Mechanical & Enclosure Engineering Specification (IP67)

## 1. Environmental & Ingress Protection Rating

The Proof-of-Weeding edge observation node must survive multi-season exposure in open agricultural fields without maintenance.

- **Target Ingress Rating:** **IEC 60529 IP67**
  - **Dust:** IP6X (Talcom dust vacuum test at 2 kPa underpressure for 8 hours with zero particulate ingress).
  - **Water:** IPX7 (Immersion in 1.0 meter water column for 30 minutes with zero moisture ingress).
- **Temperature Rating:** $-20^\circ\text{C}$ to $+65^\circ\text{C}$ ambient operational range.
- **UV Resistance:** UL 746C (f1) rated for outdoor weatherability and 10-year solar UV-C stability.

---

## 2. Enclosure Architecture & Materials

```
                 +-----------------------------+
                 |  Solar Glare & Rain Visor   |
                 +--------------+--------------+
                                |
 +------------------------------v-------------------------------+
 |  Main Top Shell (UV-Stabilized Polycarbonate / ASA)          |
 |  - Tongue-and-Groove Perimeter Channel                       |
 |  - Continuous EPDM Silicone O-Ring Cord (1.5mm diameter)     |
 +------------------------------+-------------------------------+
                                |
 +------------------------------v-------------------------------+
 |  Optical Port Assembly:                                      |
 |  - 2.0mm Borosilicate Glass Disc (AR coated, Hydrophobic)    |
 |  - Internal Nitrile O-Ring Seal                              |
 |  - Screw-down Retention Bezel                                |
 +------------------------------+-------------------------------+
                                |
 +------------------------------v-------------------------------+
 |  Base Housing & Mounting Plate:                              |
 |  - Threaded Brass Inserts (M3 x 4mm, Heat-Set)               |
 |  - Dual U-Bolt Slots for 1.5" to 2.5" Fence Posts / Poles     |
 |  - Ball-Joint Swivel Mount (30° - 45° Downward Depression)   |
 +--------------------------------------------------------------+
```

### 2.1 Material Selection
- **Injection Molding Production:** UV-stabilized Polycarbonate (Bayer Makrolon 2807 / Sabic Lexan EXL9330) with UL94 V-0 flame rating.
- **Rapid Prototyping:** FDM printed ASA (Acrylonitrile Styrene Acrylate) annealed at 85°C for layer bonding and dimensional stability.

### 2.2 Sealing Mechanism
- Continuous perimeter tongue-and-groove channel with 25% nominal compression on a Shore A 60 silicone elastomer hollow cord ($1.5\,\text{mm}$ cross-section).
- Fasteners: 6 $\times$ M3 A4 marine-grade (316) stainless steel socket head cap screws engaging heat-set brass threaded inserts.

---

## 3. Optical Window & Drip Hood

To preserve sub-millimeter vegetation change detection:
1. **Glass Composition:** High-transmittance (99.2% visible spectrum) borosilicate glass disc, diameter $28.0\,\text{mm} \times 2.0\,\text{mm}$ thickness.
2. **Surface Coatings:**
   - External: Hydrophobic and oleophobic fluoropolymer nano-coating ($> 110^\circ$ water contact angle) ensuring rain beads roll off rapidly.
   - Internal: Anti-reflective dual-sided broadband coating (BBAR $400-700\,\text{nm}$) to eliminate internal lens flare.
3. **Overhanging Weather Visor:** A $35\,\text{mm}$ forward brow inclined at $25^\circ$ downward shields the glass face from vertical driving rain, bird droppings, and overhead solar midday glare.

---

## 4. Mounting & Rigidity Constraints

- Fixed Field ROI Guarantee: The evidence protocol requires that the camera field of view does not shift between Baseline ($t_0$), Completion ($t_1$), and Follow-up ($t_2$).
- Mechanical Swivel Lock: Integrated radial tooth splines ($5^\circ$ increments) with an M6 stainless carriage bolt clamp prevent wind-induced vibration or sagging.
- Attachment Interface: Dual 316 stainless steel jubilee band clamps or M6 U-bolts securing to standard galvanized farm fence posts (40 mm to 60 mm OD).

