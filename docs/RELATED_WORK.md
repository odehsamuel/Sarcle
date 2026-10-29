# Related Work: Escrow & Oracle Patterns on Stellar/Soroban

> **Document Type:** Literature Review & Comparative Analysis  
> **Status:** Testnet Prototype v0.1  
> **Integrity Statement:** All cited repositories and issues are public open-source implementations on GitHub within the Stellar/Soroban ecosystem. No claims of unprecedented novelty are made; Proof-of-Weeding builds upon established patterns while addressing unique edge-sensor verification challenges.

---

## 1. Overview

Decentralized escrow and external data verification on Stellar have evolved rapidly since the launch of Soroban (Stellar's smart contract platform). This document reviews existing open-source projects in the Soroban ecosystem and contrasts their design choices with the Proof-of-Weeding protocol.

---

## 2. Survey of Verified Soroban Projects

### 1. `StellarDevHub/soroban-playground` (Issue #1040)
- **Title:** *Parametric Crop Insurance Smart Contract using Oracle Weather Feed*
- **Repository:** [`stellar/soroban-examples`](https://github.com/stellar/soroban-examples) / Community contributions in `StellarDevHub/soroban-playground`
- **Architecture:** Demonstrates a parametric insurance smart contract that ingests weather oracle feeds (such as cumulative rainfall or drought indices) to trigger automated claim disbursements to farmers without manual claims adjusters.
- **Comparison with Proof-of-Weeding:**
  - *Data Source:* Uses macro-level regional oracle feeds (e.g., regional NOAA satellite or station data).
  - *Proof-of-Weeding Difference:* Proof-of-Weeding operates at the **micro-plot level**, verifying localized physical labor via fixed-camera edge microcontrollers with native Ed25519 signing rather than third-party weather API feeds.

---

### 2. `Open-Hub-Tec/yucu-protocol` (Issue #26)
- **Title:** *Soroban Milestone Escrow Contract*
- **Repository:** [`Open-Hub-Tec/yucu-protocol`](https://github.com/Open-Hub-Tec)
- **Architecture:** A multi-party milestone escrow contract for freelance and service agreements on Soroban. Clients deposit funds that unlock sequentially as predefined milestones are completed, with an arbiter address assigned for dispute resolution.
- **Comparison with Proof-of-Weeding:**
  - *Milestone Attestation:* Relies on subjective mutual agreement between client and service provider, or manual arbiter judgment upon dispute.
  - *Proof-of-Weeding Difference:* Replaces subjective human sign-off with an **automated, evidence-gated release rule**. Funds are unlocked by reproducible computer vision consensus, and biological retainage guards against rapid weed regrowth.

---

### 3. `Samrat25/stellar-escrow-flow`
- **Title:** *Milestone Escrow with IPFS Work Proofs*
- **Repository:** [`Samrat25/stellar-escrow-flow`](https://github.com/Samrat25/stellar-escrow-flow)
- **Architecture:** Implements milestone-based escrow on Stellar, where workers upload proof artifacts (documents, designs, or photos) to IPFS and attach the IPFS CID to the on-chain contract state for employer review.
- **Comparison with Proof-of-Weeding:**
  - *Proof Mechanism:* The on-chain contract stores the IPFS CID as an opaque hash, but has no mechanism to verify the validity, freshness, or provenance of the uploaded file.
  - *Proof-of-Weeding Difference:* Implements on-chain challenge-response freshness (`challenge: BytesN<16>`), strictly increasing monotonic device counters (`counter: u64`), on-chain Ed25519 signature checks, and dual-attester consensus before evidence is accepted.

---

### 4. `Sahveli01/soroban-oracle-safety` & Reflector (SEP-40)
- **Title:** *Soroban Oracle Safety Protocols & Reflector Decentralized Price Feeds*
- **Specification:** SEP-40 (*Asset Price Feeds Oracle Interface*)
- **Architecture:** Standardized interfaces for multi-source price oracles on Soroban. Feeds aggregate exchange prices from multiple nodes, compute median values, track round numbers, and filter outliers.
- **Comparison with Proof-of-Weeding:**
  - *Domain:* Financial market data (cryptocurrency and forex exchange rates) updated continuously in high-frequency rounds.
  - *Proof-of-Weeding Difference:* Adapts the multi-source quorum pattern to **spatial computer vision data**. Rather than tracking median price, `evidence_registry` pairs distinct algorithm families (chromaticity Excess Green vs. fixed-point CIELAB $a^*$), enforces a maximum divergence threshold (500 bps), and verifies sensor-layer cryptographic authenticity.

---

## 3. Comparison Matrix

| Feature | `soroban-playground` #1040 | `yucu-protocol` #26 | `stellar-escrow-flow` | Reflector (SEP-40) | **Proof-of-Weeding** |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Domain** | Parametric Insurance | Service Escrow | Freelance Escrow | Financial Oracles | **Vegetation Clearing Escrow** |
| **Verification Basis** | Weather API Feed | Subjective Sign-off | IPFS CID Pinning | Aggregated Node Prices | **Edge-Signed CV Quorum** |
| **Edge Hardware Identity** | None | None | None | Node Validators | **ESP32-CAM (Ed25519 Keys)** |
| **Replay Protection** | Timestamp check | None | Nonce / Sequence | Round ID | **16B Registry PRNG + NVS Counter** |
| **Retainage Lockup** | N/A | Optional | No | N/A | **Enforced Biological Retainage** |
| **Public Re-Verification**| N/A | N/A | View IPFS file | N/A | **`pow-verify` Deterministic CLI** |

---

## 4. Summary & Synthesis

Existing Soroban implementations provide strong foundations for financial price feeds and multi-party payment settlement. Proof-of-Weeding fills the void between physical real-world labor and on-chain capital allocation by establishing a verifiable evidence registry that enforces cryptographic authenticity from low-cost edge sensors before escrowed funds can be released.
