# Security Policy

## 1. Scope & Status Notice

**Proof-of-Weeding** is an open-source testnet research prototype. It is **NOT** currently audited for mainnet asset handling. Do not lock real economic value or mainnet tokens in these contracts.

---

## 2. Supported Versions

| Version | Supported | Description |
| :--- | :---: | :--- |
| `0.1.x` (Testnet) | :white_check_mark: | Active research & testing prototype |
| `< 0.1.0` | :x: | Deprecated pre-release drafts |

---

## 3. Threat Model & Out-of-Scope Vulnerabilities

Before submitting a vulnerability report, please review [`docs/THREAT_MODEL.md`](file:///c:/Users/USER/Projects/Sarcle/docs/THREAT_MODEL.md).

The following known physical constraints are **out of scope** for bug bounties or security advisories at this prototype stage:
- **Physical Camera Tampering:** Unencrypted physical access to the ESP32 developer microcontroller UART/flash pins (firmware flash encryption and secure boot are explicitly documented as `TODO`).
- **Real-World Plant Mimicry:** Realistic high-fidelity artificial plants or specialized green paint that fools classical Excess Green chromaticity within the configured divergence tolerance.
- **Single-Operator Collusion in v0.1:** Attester A and Attester B running on the same host machine in testnet mode. Dual-independent node operator networks are targeted for v0.2.

---

## 4. Reporting a Vulnerability

If you discover a vulnerability affecting the smart contracts (`contracts/evidence_registry` or `contracts/work_escrow`), cryptographic verification logic (`tools/ed25519_compact.py` or signature parsing), or attester quality gates:

1. **Do not create a public GitHub issue.**
2. Send an email to the security point of contact at: `security@proof-of-weeding.internal` (or message the repository maintainers via GitHub private vulnerability reporting).
3. Include:
   - Detailed description of the vulnerability.
   - Proof-of-concept (PoC) code or reproduction steps.
   - Assessment of potential impact (e.g. fund drainage, challenge replay, signature bypass).

### Response SLA
- **Initial Acknowledgement:** Within 48 hours.
- **Triage & Status Update:** Within 5 business days.
- **Resolution / Patch:** Target 14 business days depending on complexity.

We appreciate the responsible disclosure of security issues and will credit researchers in our release notes.
