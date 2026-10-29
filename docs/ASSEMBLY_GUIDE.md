# Factory Assembly, Flashing & Field Deployment Guide

## 1. Scope & Objective

This document defines the standard operating procedure (SOP) for factory manufacturing, secure cryptographic provisioning, mechanical sealing, and agricultural field installation of the **Proof-of-Weeding (PoW)** edge camera node.

---

## 2. Stage 1: Factory Flashing & Hardware Provisioning

All flashing and security hardening must be conducted via the 12-pin Bed-of-Nails test fixture before the board is installed into its enclosure.

```
       +------------------------------------+
       |  Bed-of-Nails Pogo Pin Fixture     |
       |  (GND, 3V3, TX, RX, IO0, EN, RST)  |
       +-----------------+------------------+
                         │
                         v
       +------------------------------------+
       |  1. Flash firmware binaries        |
       |     bootloader.bin + partitions.bin|
       +-----------------+------------------+
                         │
                         v
       +------------------------------------+
       |  2. provision_device.py            |
       |     - Generate device Ed25519 seed |
       |     - Burn encrypted NVS pow_sec   |
       |     - Register Device ID on Stellar|
       +-----------------+------------------+
                         │
                         v
       +------------------------------------+
       |  3. Hardware Hardening (eFuses)    |
       |     - enable_flash_encryption.py   |
       |     - secure_boot_sign.py          |
       |     - disable_jtag_efuse.py        |
       +------------------------------------+
```

### 2.1 Tooling Commands
```bash
# Step A: Generate device Ed25519 identity and register on-chain
python tools/provisioning/provision_device.py --chain-mode testnet --output-csv build/factory_keys.csv

# Step B: Provision flash encryption and burn AES-XTS key into BLK_KEY0
python tools/provisioning/enable_flash_encryption.py --target esp32s3 --burn-efuse

# Step C: Sign bootloader and firmware with Secure Boot v2 digest
python tools/provisioning/secure_boot_sign.py --input-bin build/firmware.bin --output-bin build/firmware_signed.bin

# Step D: Permanently sever hardware debug taps (JTAG / UART download mode)
python tools/provisioning/disable_jtag_efuse.py --target esp32s3 --execute
```

---

## 3. Stage 2: Mechanical Assembly & IP67 Sealing

1. **Brass Threaded Inserts:** Heat-press 6 $\times$ M3 brass threaded inserts into the housing bosses using a temperature-regulated soldering iron set to $210^\circ\text{C} \pm 5^\circ\text{C}$.
2. **Optical Borosilicate Window:**
   - Clean the $28.0 \times 2.0\,\text{mm}$ glass disc with optical-grade isopropanol.
   - Insert Nitrile O-ring into the front face recess.
   - Place the glass disc with hydrophobic nano-coating facing outwards.
   - Tighten the retaining bezel screws in a cross pattern to $0.35\,\text{N}\cdot\text{m}$.
3. **Desiccant Sachet Insertion:** Slid one factory-fresh 5-gram Silica Gel sachet into the lower retaining rib. The enclosure must be closed within 15 minutes of opening the desiccant pouch.
4. **ePTFE Vent Installation:** Snap the Gore PMF100318 pressure equalization vent into the vent aperture until the retention barb clicks securely into place.
5. **Enclosure Closure:** Fit the $1.5\,\text{mm}$ silicone gasket cord into the perimeter channel. Fasten the 6 stainless M3 cap screws with a calibrated torque screwdriver set to $0.55\,\text{N}\cdot\text{m}$.

---

## 4. Stage 3: Field Deployment & Calibration Checklist

| Step | Action | Verification / Pass Criteria |
| :--- | :--- | :--- |
| **1** | **Fence Post Mounting** | Clamp node securely to a $40-60\,\text{mm}$ galvanized steel post at $1.8\text{m} - 2.2\text{m}$ height above ground. |
| **2** | **Depression Angle** | Lock the swivel mount at $35^\circ$ downward tilt aiming at the designated weeding area. Ensure the camera frame fully bounds the clearing parcel. |
| **3** | **Solar Panel Orientation**| Angle solar panel towards true South (Northern Hemisphere) or true North (Southern Hemisphere) inclined at latitude $+ 10^\circ$. |
| **4** | **Lens Cleanliness** | Verify that no fingerprint oil, packaging debris, or plastic film remains on the front glass aperture. |
| **5** | **Baseline Capture ($t_0$)** | Power on device. Verify via cellular indicator LED that challenge was fetched, frame signed, and baseline registered in `evidence_registry`. |
| **6** | **ROI Definition** | In the farmer dashboard, trace the polygon ROI coordinates conforming to `docs/spec/roi-format.md` and lock job escrow. |
