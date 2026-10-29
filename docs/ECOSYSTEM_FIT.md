# Ecosystem Fit: Reusable Device-Signed Evidence on Stellar

> **Document Type:** Architecture & Integration Guide  
> **Target Audience:** Stellar & Soroban smart contract developers, IoT hardware builders, oracle designers  
> **Status:** Testnet Prototype v0.1

---

## 1. The Physical-to-Digital Gap in Stellar Smart Contracts

Stellar excels at high-throughput, low-latency financial settlement, asset issuance (SEP-41), and payment routing. With Soroban, Turing-complete state machines can programmatically lock, release, or penalize capital based on arbitrary logical conditions.

However, almost all deployed Soroban protocols rely either on:
1. **Financial price feeds:** E.g., SEP-40 decentralized exchange / market price oracles.
2. **Off-chain human signers:** Multi-sig escrow arrangements where individuals manually verify real-world conditions.

**Proof-of-Weeding** introduces an open, reusable architectural pattern for **Edge-Attested Physical Evidence**. In this model:
- Physical edge devices (microcontrollers, cameras, environmental sensors) sign data payloads using native Ed25519 cryptographic keys.
- Independent off-chain attesters execute deterministic, reproducible verification algorithms.
- A decoupled evidence layer (`evidence_registry`) verifies cryptographic provenance, replay protection, and multi-attester consensus on-chain.
- Application-specific smart contracts (`work_escrow` or third-party dApps) query or attach accepted evidence to trigger automated capital transfers.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        PHYSICAL EDGE DEVICES                           │
│  [ESP32 Camera]       [Solar Meter]       [Cold-Chain Temp Logger]     │
│         │                   │                        │                 │
│         └─────────── Ed25519 Signed Payloads ────────┘                 │
└─────────────────────────────────┬──────────────────────────────────────┘
                                  ▼
┌────────────────────────────────────────────────────────────────────────┐
│                    OFF-CHAIN ATTESTER NETWORK                          │
│   Attester A (Python / OpenCV)       Attester B (Rust / Fixed-Point)   │
│   - Fetches on-chain challenge       - Runs independent verification   │
│   - Validates quality gates          - Submits analysis hash & value   │
└─────────────────────────────────┬──────────────────────────────────────┘
                                  ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   SOROBAN EVIDENCE LAYER (REUSABLE)                    │
│   `evidence_registry` Contract                                         │
│   - Enforces device registry & revocations                             │
│   - Verifies 16-byte fresh PRNG challenges & monotonic counters        │
│   - Enforces multi-attester quorum & algorithmic diversity             │
│   - Computes consensus integer mean or flags divergence                │
└─────────────────────────────────┬──────────────────────────────────────┘
                                  ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     APPLICATION LAYER CONSUMERS                        │
│   ┌────────────────────┐ ┌───────────────────┐ ┌───────────────────┐   │
│   │   `work_escrow`    │ │ Solar Micro-Grid  │ │ Cold-Chain Escrow │   │
│   │ (Proof-of-Weeding) │ │ (Renewable REC)   │ │ (Pharma Logistics)│   │
│   └────────────────────┘ └───────────────────┘ └───────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Decoupled Architecture: `evidence_registry` vs `work_escrow`

A fundamental design requirement of Proof-of-Weeding was avoiding tightly coupled escrow and verification logic.

| Contract | Responsibility | Application Specific? |
| :--- | :--- | :---: |
| `evidence_registry` | Device identity, challenge issuance, signature verification, monotonic counter replay prevention, allowlisted analyzer consensus. | **No** (Generic / Reusable) |
| `work_escrow` | Locked tokens, farmer/worker identities, milestone rules, retainage, dispute windows, arbiter fallback. | **Yes** (Proof-of-Weeding Specific) |

Because `evidence_registry` stores observations under an opaque `job_ref: u64`, any external Soroban contract can reference registered devices and observations without modifying a single line of registry code.

---

## 3. Potential Ecosystem Use Cases

### A. Solar Micro-Grid Power Generation (Renewable Energy Credits)
- **Problem:** Solar micro-grid operators in developing markets want to issue tokenized renewable energy credits (RECs) or release micro-lease payments based on verified kilowatt-hours generated.
- **Integration:**
  - Micro-inverter or smart meter acts as the registered `device_id`.
  - Signed payload includes total active energy (kWh) and meter counter.
  - Analyzers verify meter calibration and grid frequency validity.
  - `evidence_registry` records the verified power generation under `metric_id = 101` (`solar_kwh_generated`).
  - A Soroban REC token contract mints tokens proportionally to accepted observations.

### B. Cold-Chain Pharmaceutical & Perishable Logistics
- **Problem:** Shippers of vaccines or fresh produce require payment escrows where freight fees are deducted if internal container temperatures breach acceptable ranges ($2^\circ\text{C} - 8^\circ\text{C}$).
- **Integration:**
  - BLE or Cellular temperature datalogger signs hourly temperature observations with registry-issued challenges.
  - Attesters verify checksum integrity and check for sensor calibration drift.
  - Escrow contract releases carrier funds upon delivery only if all intermediate observations in `evidence_registry` satisfy temperature bounds.

### C. Parametric Micro-Insurance (Drought & Flood Triggering)
- **Problem:** Smallholder farmers need immediate, automated claim payouts when local rain gauges or moisture sensors record severe drought, without waiting for manual loss adjustment.
- **Integration:**
  - Ground-based soil moisture probes report daily volumetric water content (VWC).
  - Multi-attester quorum validates sensor telemetry against regional satellite indicators.
  - Insurance smart contract releases automatic indemnity payouts if soil moisture remains below trigger thresholds for consecutive intervals.

---

## 4. Comparison with Existing Stellar Oracle Patterns

| Dimension | Standard Stellar Price Feeds (Reflector / SEP-40) | Multi-Sig Human Escrow | Proof-of-Weeding (`evidence_registry`) |
| :--- | :--- | :--- | :--- |
| **Data Source** | Centralized exchanges, liquidity pools | Human inspection / photos | **Edge microcontrollers with native Ed25519 keys** |
| **Data Frequency** | Continuous / High frequency (seconds/minutes) | Infrequent / Manual (days/weeks) | **Episodic / Challenge-gated on-demand** |
| **Replay Protection** | Sequence numbers & ledger timestamps | Human review | **16-byte on-chain PRNG challenge + Monotonic NVS counter** |
| **Analysis Verification** | Median calculation of published prices | Subjective human opinion | **Dual-implementation CV quorum + public re-verifier CLI** |
| **Storage Model** | Ephemeral / Rolling window | Contract state | **Persistent instance TTL extended on every interaction** |
| **Failure Modes** | Oracle price manipulation / sandwiching | Human bribery, delay, subjective bias | **Physical camera tampering, device key theft** |

---

## 5. Developer Guide: Integrating `evidence_registry`

External Soroban smart contracts can consume observations from `evidence_registry` using the cross-contract call pattern:

```rust
use soroban_sdk::{contractclient, Address, Env};

// Import client interface for evidence_registry
#[contractclient(name = "EvidenceRegistryClient")]
pub trait EvidenceRegistryInterface {
    fn get_observation(env: Env, obs_id: u64) -> Observation;
}

pub fn verify_milestone(env: &Env, registry_address: Address, obs_id: u64, expected_job_ref: u64) {
    let client = EvidenceRegistryClient::new(env, &registry_address);
    let obs = client.get_observation(&obs_id);
    
    // 1. Verify observation belongs to this job
    assert!(obs.job_ref == expected_job_ref, "Mismatched job ref");
    
    // 2. Ensure consensus was reached
    assert!(obs.status == ObservationStatus::Accepted, "Observation not accepted");
    
    // 3. Evaluate accepted measurement
    let measurement_bps = obs.accepted_value_bps;
    // ... execute application-specific release logic ...
}
```

---

## 6. Trust Requirements & Roadmap to Decentralized Attestation

In the current v0.1 testnet prototype, both Attester A and Attester B are operated in the same testing environment. For production ecosystem adoption, the following roadmap is required:

1. **Independent Attester Node Operators:** Attesters run as independent cloud or edge services with staked collateral in a registry slashing pool.
2. **Deterministic Sandbox WASM Analyzers:** Offloading the CV algorithms from native Python/Rust into isolated WebAssembly sandboxes (e.g. WasmEdge) to ensure identical IEEE 754 floating point and rasterization behavior across operating systems.
3. **Hardware Enclaves:** Provisioning edge camera devices with secure elements (e.g. ATECC608A or ESP32-S3 eFuse Secure Boot) to prevent private key extraction upon physical capture.
