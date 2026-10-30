# Hardware Reference Architecture Design

## 1. System Overview

The **Proof-of-Weeding (PoW)** edge capture node is an autonomous, solar-powered agricultural observation camera designed to verify ground vegetation clearance under harsh field environments.

```
       +--------------------+
       |  Solar Panel 6V 3W |
       +---------+----------+
                 |
                 v
       +--------------------+          +---------------------+
       |   CN3791 MPPT IC   | -------->| 18650 LiFePO4 Cell  |
       +---------+----------+          | 3.2V / 3200 mAh     |
                 |                     +----------+----------+
                 v                                |
       +--------------------+                     |
       | AP2112K 3.3V LDO   |<--------------------+
       +---------+----------+
                 |
     +-----------+-----------+
     |                       |
     v                       v
+----+----------------+  +---+------------------+
| ESP32-S3 / ESP32    |  | Power Gated Rails    |
| Microcontroller     |  | - PMOS Camera Rail   |
| (Secure Boot v2)    |  | - PMOS Modem Rail    |
+----+-----------+----+  +---+-------------+----+
     |           |           |             |
     v           v           v             v
+----+-----+ +---+----+ +----+-----+ +-----+----+
| Ed25519  | | Flash  | | OV2640   | | Quectel  |
| Hardware | | AES-XTS| | OV5640   | | BG95-M3  |
| Engine   | | Encrypt| | Camera   | | Modem    |
+----------+ +--------+ +----------+ +----------+
```

## 2. Key Subsystems

### 2.1 Microcontroller Unit (MCU)
- **Primary Target:** ESP32-S3-WROOM-1-N8R8 (8 MB Flash, 8 MB Octal PSRAM).
- **Secondary Target:** Classic ESP32-WROVER-E (16 MB Flash, 8 MB Quad PSRAM).
- **Hardware Security Capabilities:**
  - Dedicated hardware SHA-256 and AES accelerators.
  - Flash encryption via AES-128/256-XTS engine.
  - Secure Boot v2 RSA-3072 / ECDSA digital signature engine.
  - One-Time-Programmable (eFuse) blocks for permanent key provisioning and JTAG debug disablement.

### 2.2 Solar Harvester & Energy Storage
- **Solar Input:** 6V monocrystalline panel ($150 \times 130\text{ mm}$, 3W peak).
- **MPPT Controller:** Consonance CN3791 PWM step-down battery charger with Maximum Power Point Tracking.
- **Battery Chemistries Supported:**
  - Lithium Iron Phosphate ($\text{LiFePO}_4$, 3.2V nominal, 3.65V cutoff) for 2000+ cycle thermal durability (-20°C to +65°C).
  - Lithium-Ion (18650, 3.7V nominal, 4.2V cutoff) with thermistor NTC monitoring.

### 2.3 Optical Imaging
- **Sensors:** OmniVision OV2640 (UXGA 1600x1200) or OV5640 (5MP QSXGA).
- **Lens Mount:** M12 $\times 0.5$ mount with 120° Wide-Angle lens (IR-cut coated).
- **FPC Pinout:** Standard 24-pin DVP parallel interface with dedicated PMOS high-side rail gate.

### 2.4 Cellular Telemetry
- **Quectel BG95-M3 / SIMCom SIM7080G:** Multi-mode LTE Cat-M1 / Cat-NB2 / EGPRS.
- **Antenna:** Internal high-gain flex PCB antenna (698–960 MHz / 1710–2690 MHz).
- **SIM:** Standard nano-SIM (4FF) socket with TVS diode protection (USBLC6-2SC6) against electrostatic discharge.

## 3. PCB Layout & Manufacturing Rules
- 4-layer FR4 stackup: Signal / GND plane / Power plane / Signal.
- Impedance controlled $50\,\Omega$ coplanar RF microstrip lines for cellular antenna.
- Decoupling capacitor placement: $< 2\text{ mm}$ from MCU and camera sensor power pins.
- 12 Test points exposed on bottom copper layer for automated Bed-of-Nails testing.

