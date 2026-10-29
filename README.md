# Proof-of-Weeding (PoW)

> **Testnet Prototype Notice:**  
> Proof-of-Weeding is an experimental research prototype on the Stellar/Soroban Testnet.  
> It is **NOT** a production payment system, **NOT** an agricultural insurance product, and **NOT** a labor employment service.  
> Do not use with mainnet assets or real-world contractual obligations.

---

## 1. Scope of the Claim

Proof-of-Weeding measures relative change in **total green vegetation cover** inside a fixed region of interest (ROI) over time.

> **CRITICAL AGRICULTURAL SCOPE:**  
> The system does **NOT** distinguish weeds from cash crops or desirable plants.  
> Jobs must strictly target zones where **all vegetation is intended to be cleared** (such as fallow beds between plantings, access roads, firebreaks, drainage canals, and irrigation borders).  
> The smart contracts **cannot verify image contents**. Contracts verify device Ed25519 signatures, challenge freshness, monotonic replay counters, allowlisted analyzer hashes, quorum agreement between independent implementations, and dispute challenge windows.

---

## 2. Clean-Room & Integrity Statement

This repository is built under strict clean-room rules:
- **No third-party datasets** (no Kaggle, ImageNet, PlantDoc, or proprietary farm imagery).
- **No machine learning models or pretrained weights** (all analyzers are classical computer vision with explicit mathematical parameters).
- **No real field imagery**: Every test scene is generated procedurally in this repository using NumPy and PIL mathematical noise.
- **Zero invented metrics or benchmarks**: Reported numbers are empirical results on procedurally generated synthetic textures labeled as synthetic.

---

## 3. Architecture

```
                                ┌────────────── evidence_registry (Soroban) ──────────────┐
ESP32-CAM ──signed frame──▶ Attester A (Python/OpenCV) ──┐   devices, analyzers, attesters, challenges,
 (fetches challenge first)  Attester B (Rust analyzer)  ──┼─▶ observations, agreement check
                                                          │                  ▲
                                                          │                  │ reads
                                      work_escrow (Soroban) ◀── attach_observation ── dashboard (Freighter)
                                      jobs, funds, retainage, disputes
```

### Trust Assumptions
- **Edge Devices**: Device private keys are trusted only if hardware is physically secured. Flash encryption and secure boot are marked `TODO`.
- **Attesters**: In v0.1, Attester A and Attester B are operated by the same party; independence is of programming language, cryptographic keys, and algorithmic implementation (chromaticity Excess Green vs. fixed-point CIELAB $a^*$), not of legal entity.
- **Arbiter**: The designated per-job arbiter is trusted to resolve disputes and unresolvable analyzer divergences.

---

## 4. Status Table

| Component | Feature / Capability | Priority | Status | Notes |
| :--- | :--- | :---: | :---: | :--- |
| **Observation Spec** | 115-byte canonical binary format v2 | P0 | **Implemented** | `docs/spec/observation-format.md` |
| **Test Vectors** | 8 deterministic cross-language vectors | P0 | **Implemented** | `docs/spec/test-vectors.json` |
| **Contract A** | `evidence_registry` contract & tests | P0 | **Implemented** | Storage TTL extension, monotonic counter, quorum |
| **Contract B** | `work_escrow` core release rule (integer math) | P0 | **Implemented** | `comp * 10000 <= base * (10000 - thresh)` |
| **Contract B** | Retainage lockup & follow-up regrowth check | P1 | **Implemented** | `followup_cover <= comp + max_regrowth` |
| **Synthetic Scenes** | Procedural soil & weed generation | P0 | **Implemented** | Zero external data, pure mathematical noise |
| **Device Simulator** | Keypair generation, signing, posting | P0 | **Implemented** | Full pipeline runs with zero hardware |
| **Attester A** | Python/Flask + OpenCV ExG + Quality Gates | P0 | **Implemented** | Blur, exposure, homography displacement checks |
| **Attester B** | Rust CLI fixed-point CIELAB $a^*$ analyzer | P1 | **Implemented** | `attester-b/` independent crate & runner |
| **Calibration** | 50-scene empirical calibration report | P1 | **Implemented** | Mean divergence 152 bps across synthetic scenes |
| **Public Verifier** | `pow-verify` public auditing CLI | P1 | **Implemented** | `tools/pow-verify/verify.py` |
| **ESP32-CAM** | PlatformIO Arduino firmware (C++) | P1 | **Stub / Unverified** | Unverified on physical silicon |
| **Dashboard** | React + Vite + TypeScript web interface | P2 | **Implemented** | Create Job, Job Detail, Arbiter, Registry |
| **Metric 2 & 3** | `bare_soil_fraction`, `canopy_gap_fraction` | P2 | **Specified Stub** | Defined in `docs/spec/metrics.md` |

---

## 5. Quickstart: Running the End-to-End Simulation

You can run the full protocol pipeline without physical hardware or testnet tokens in under 10 seconds:

```bash
# 1. Run the full end-to-end simulation
python scripts/e2e_sim.py

# 2. Run the public evidence re-verifier on the simulated job
python tools/pow-verify/verify.py --job-id 1 \
  --image-dir attester-a/storage/images \
  --roi-file attester-a/storage/rois/084e1a3f688169af5cd3030c5dadf272006d94a4d6d1d7f5406d5a5daa764d04.json

# 3. Run all unit tests
python -m unittest discover tests
```

---

## 6. Monorepo Structure

```
proof-of-weeding/
├─ contracts/
│  ├─ evidence_registry/            # Reusable, job-agnostic evidence layer (Soroban Rust)
│  └─ work_escrow/                  # Job funds, state machine, retainage (Soroban Rust)
├─ attester-a/                      # Python, Flask, OpenCV ExG analyzer, quality gates
├─ attester-b/                      # Rust analyzer CLI + runner (CIELAB a* fixed-point)
├─ tools/
│  ├─ synthetic-scenes/             # Procedural field generator with known ground truth
│  ├─ device-simulator/             # Signs and posts frames, zero hardware required
│  ├─ pow-verify/                   # Public re-verification CLI
│  └─ calibrate_analyzers.py        # 50-scene cross-analyzer calibration suite
├─ firmware/esp32cam/               # PlatformIO Arduino C++ edge firmware
├─ dashboard/                       # React + Vite + TypeScript web UI
├─ docs/                            # Specs, Threat Model, Related Work, Ecosystem Fit
├─ scripts/                         # deploy_testnet.py, e2e_sim.py
└─ tests/                           # Complete cross-language test suites
```

---

## 7. Key Documentation

- [Threat Model (12 Attack Vectors & Mitigations)](docs/THREAT_MODEL.md)
- [Ecosystem Fit & Reusable Evidence Layer](docs/ECOSYSTEM_FIT.md)
- [Related Work in the Stellar/Soroban Ecosystem](docs/RELATED_WORK.md)
- [Seed Issues: 20 Actionable Community Tasks](docs/ISSUES_SEED.md)
- [Pinned Tooling & Dependency Versions](docs/VERSIONS.md)
- [Observation Format Specification (115-Byte Canonical)](docs/spec/observation-format.md)
- [Region-of-Interest (ROI) Polygon Specification](docs/spec/roi-format.md)
- [Metric Definitions & Extensibility Spec](docs/spec/metrics.md)
- [Empirical Analyzer Calibration Report](docs/calibration-report.json)
- [Contributing & Clean-Room Rules](CONTRIBUTING.md)
- [Security Disclosure Policy](SECURITY.md)

---

## 8. License

Distributed under the MIT License. See [LICENSE](LICENSE) for details.
