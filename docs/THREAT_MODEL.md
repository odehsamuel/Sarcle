# Threat Model: Proof-of-Weeding

> **Classification:** Security & Trust Analysis Specification  
> **Status:** Draft / Prototype v0.1  
> **Protocol:** Proof-of-Weeding (Stellar / Soroban)  
> **Applicability:** Autonomous smart contract escrow gated by device-signed edge computer vision.

---

## 1. Executive Summary & Non-Goals

Proof-of-Weeding bridges real-world physical ground labor with Stellar smart contracts using an edge-to-oracle pipeline. **The smart contracts themselves cannot inspect raw pixels.** Instead, they evaluate cryptographic integrity, stateful replay counters, temporal freshness, allowlisted multi-party oracle quorums, and dispute time-locks.

### Core Non-Goals & Trust Boundaries
- **Not Mainnet Ready:** This protocol is a research prototype deployed to the Stellar Testnet.
- **Not an ML / AI Oracle:** Image evaluation relies solely on deterministic, classical color-space algorithms (Excess Green index and CIELAB $a^*$). No neural networks or black-box classifiers are used.
- **Agricultural Scope:** The protocol measures gross reduction in green vegetative cover inside a fixed region of interest (ROI). It does **not** identify weed taxonomy or differentiate cash crops from invasive species.
- **Edge Key Trust:** Edge devices are assumed vulnerable to physical extraction unless provisioned with hardware secure elements, flash encryption, and secure boot (marked as `TODO` in firmware).

---

## 2. System Architecture & Assets at Risk

### Assets at Risk
1. **Escrowed Tokens:** Funds locked by the farmer in `work_escrow` pending milestone evidence.
2. **Retainage Deposit:** A percentage (e.g. 20%) held back to guard against rapid biological regrowth.
3. **On-Chain Reputation & Registry Records:** Valid observations in `evidence_registry` used for verification.
4. **Device Private Key:** Ed25519 seed stored on the camera microcontroller.

---

## 3. Comprehensive Attack Vector Analysis (12 Vectors)

The following matrix documents the primary attack vectors, their mechanics, severity, mitigation implementation, and residual risk.

---

### Vector 1: Photo / Screen Replay Attack
- **Attack Mechanic:** An adversary places a smartphone screen, high-resolution tablet, or laminated color printout of a cleared field in front of the fixed camera lens during the completion phase.
- **Severity:** High
- **Mitigation:**
  1. *Challenge Freshness:* The device must obtain an on-chain ephemeral 16-byte challenge before capturing and signing the frame.
  2. *Quality Gates (Homography & Lighting):* Screen backlights emit polarized, narrow-spectrum RGB light that causes chromatic clipping. Attester quality gates reject frames with overexposure (`mean_luminance > 220`) or insufficient contrast.
  3. *Fixed Focal Depth & Parallax:* Cameras have a fixed hyperfocal focus calibrated to the ground (1.5–2.5m). Objects held within inches of the lens fail the Laplacian variance blur threshold (`variance < 100`).
  4. *Dispute Challenge Window:* Every completion observation is subject to a 24-hour on-chain dispute window before funds are unlocked, allowing the farmer to visually inspect the physical plot.
- **Residual Risk:** A full-scale, outdoor-placed photographic billboard positioned at the exact focal distance could bypass simple blur checks. Physical inspection during the challenge window remains the final safeguard.

---

### Vector 2: Pre-Signed Frame Replay Attack
- **Attack Mechanic:** A malicious worker captures a photo of a clean field weeks in advance, stores the signed observation, and submits it when a new job is created.
- **Severity:** Critical
- **Mitigation:**
  1. *Registry-Issued Challenge:* `evidence_registry::request_challenge` derives a 16-byte challenge from ledger sequence numbers, block timestamp, and caller inputs.
  2. *Strict Challenge TTL:* Challenges expire within `challenge_ttl_secs` (default 300 seconds). Observations submitted with expired challenges are rejected with `Error::ChallengeExpired`.
  3. *Single-Use Enforcement:* Challenges store a `used: bool` flag. Submitting an observation immediately sets `used = true`; replaying the same challenge fails with `Error::ChallengeAlreadyUsed`.
  4. *Monotonic Sequence Counter:* Devices maintain an internal monotonic counter in non-volatile storage (NVS). The registry asserts `counter > LastCounter(device_id)` and updates storage on every submission (`Error::CounterNotMonotonic`).
- **Residual Risk:** If ledger time drifts significantly, tight challenge windows could cause false-positive rejections. Tolerances are calibrated to $\pm 60$ seconds.

---

### Vector 3: Staged Scenes (Plastic Weeds & Green Spray Paint)
- **Attack Mechanic:** To satisfy the baseline requirement (`cover >= min_baseline_bps`), a worker scatters synthetic green turf or sprays green paint, captures the baseline, removes the plastic, and claims clearing rewards.
- **Severity:** Medium
- **Mitigation:**
  1. *Retainage Lockup & Follow-Up Observation:* The protocol withholds a configurable retainage (e.g. 2000 bps = 20%) for a mandatory delay (`followup_delay_secs`, e.g. 24–72 hours).
  2. *Spectral Drift:* Spray paint and dyed plastics exhibit unnatural spectral reflectance in the green chromaticity space (`g = G / (R + G + B)`).
  3. *Farmer Challenge Window:* The farmer has unilateral dispute rights during the challenge window.
- **Residual Risk:** Sophisticated staging can fool classical color-space analyzers. The arbiter dispute process is the primary backstop.

---

### Vector 4: Covering Plot with Opaque Tarps or Cardboard
- **Attack Mechanic:** Rather than uprooting weeds, a worker lays down black landscape plastic, tarps, or cardboard over the vegetation.
- **Severity:** Medium
- **Mitigation:**
  1. *Job Specification:* If the farmer's objective is weed eradication (killing weeds via solarization), mulching may be acceptable. If physical clearing is required, the baseline ROI definition must specify exposed ground.
  2. *Bare Soil Color Profile:* Attester A's chromaticity check computes chromatic distribution across the ROI. Pure black plastic or bright blue tarps produce severe deviations from standard soil chromaticity.
  3. *Follow-Up Window:* If weeds were merely covered and the cover is blown away or removed, follow-up observation detects regrowth.
- **Residual Risk:** Low-reflectance biodegradable cardboard may register as bare soil on simple color-space algorithms.

---

### Vector 5: "Haircut" Clearing (Mowing Shoots Without Root Extraction)
- **Attack Mechanic:** A worker uses a string trimmer or mower to decapitate weed stalks at surface level, leaving roots intact. Immediate completion imagery shows low green cover, but weeds re-sprout within 48–72 hours.
- **Severity:** High
- **Mitigation (Core P1 Architecture):**
  1. *Enforced Retainage Fraction:* A substantial portion of the escrow (e.g. 20–30%) is locked as retainage.
  2. *Follow-Up Observation Constraint:* Retainage is released only if a follow-up observation taken after `followup_delay_secs` demonstrates non-regrowth:
     $$\text{followup\_cover\_bps} \le \text{completion\_cover\_bps} + \text{max\_regrowth\_bps}$$
  3. *Automatic Forfeiture:* If rapid regrowth occurs, the escrow transitions to `Settled` while refunding the retainage to the farmer.
- **Residual Risk:** Weather conditions (e.g. extreme drought) might temporarily retard regrowth of intact roots beyond the follow-up window.

---

### Vector 6: Diurnal & Weather-Induced Lighting Shifts
- **Attack Mechanic:** Baseline is captured on an overcast day (diffuse light, high saturation); completion is captured under direct harsh midday sun (specular reflection, bleached greens), artificially deflating measured green cover.
- **Severity:** High
- **Mitigation:**
  1. *Normalized Chromaticity (ExG):* Attester A computes chromatic coordinates:
     $$r = \frac{R}{R+G+B}, \quad g = \frac{G}{R+G+B}, \quad b = \frac{B}{R+G+B}$$
     Excess Green ($ExG = 2g - r - b$) removes intensity scaling and isolates chromatic hue.
  2. *Fixed-Point CIELAB $a^*$ (Attester B):* Attester B converts RGB to CIELAB, evaluating negative $a^*$ values (green-red opponent channel) which separates luminance ($L^*$) from chromaticity ($a^*, b^*$).
  3. *Quality Gates:* Frames with `mean_luminance < 30` (dusk/shadow) or `mean_luminance > 220` (specular washout) are rejected outright (`OVEREXPOSED` / `UNDEREXPOSED`).
- **Residual Risk:** Deep shadows cast by adjacent trees or buildings across only half the ROI can skew threshold segmentations.

---

### Vector 7: Edge Camera Key Theft & Physical Extraction
- **Attack Mechanic:** An attacker steals the ESP32-CAM unit from the field, extracts the flash memory, recovers the Ed25519 private key, and signs arbitrary observation payloads.
- **Severity:** High
- **Mitigation:**
  1. *On-Chain Device Revocation:* The registry admin can immediately invoke `revoke_device(device_id)`. All subsequent submissions with that key are rejected (`Error::DeviceRevoked`).
  2. *Microcontroller Hardening (Firmware Roadmap):*
     - Enable ESP32 Flash Encryption (AES-XTS).
     - Burn eFuses for Secure Boot v2 (RSA/ECDSA verification of bootloader).
     - Disable JTAG hardware debugging via eFuse.
- **Residual Risk:** On standard developer ESP32 boards without burned eFuses, flash memory can be dumped via UART in under 60 seconds.

---

### Vector 8: Attester Collusion & Operator Compromise
- **Attack Mechanic:** An attester service signs false analyses, reporting 0% green cover for an untouched plot to unlock escrowed funds.
- **Severity:** Critical
- **Mitigation:**
  1. *Multi-Attester Quorum:* `evidence_registry` requires analyses from at least `quorum` (default 2) independent attesters before accepting an observation.
  2. *Distinct Algorithmic Families:* Analyses must originate from different algorithm families (`family_id` 1 = ExG, `family_id` 2 = CIELAB). Submissions with matching family IDs are rejected (`Error::DuplicateFamily`).
  3. *Divergence Threshold:* If the absolute difference between submitted values exceeds `max_divergence_bps` (500 bps = 5%), the observation is marked `Divergent` and blocked from escrow attachment.
  4. *Public Re-Verification CLI (`pow-verify`):* Because raw JPEG frames and canonical ROI files are logged off-chain with their SHA-256 hashes pinned on-chain, anyone can independently re-run the analyzers and prove attester fraud.
  5. *v0.1 Documented Limitation:* In this prototype, Attester A and B are run by the same test operator. Production deployments require independent node operators.
- **Residual Risk:** If both attesters are compromised and submit identical falsified values within 500 bps, the contract accepts the value unless challenged by the farmer.

---

### Vector 9: ROI Mismatch & Coordinate Tampering
- **Attack Mechanic:** The job specifies clearing an overgrown ditch, but the worker alters the polygon coordinates to evaluate a clean concrete walkway.
- **Severity:** Critical
- **Mitigation:**
  1. *Canonical JSON Format:* ROIs are defined in normalized image coordinates $[0.0, 1.0]$ with lexicographically sorted keys and 6-decimal fixed precision.
  2. *On-Chain Hash Pinning:* When creating the job, `work_escrow::create_job` stores `roi_hash = SHA-256(canonical_json)`.
  3. *Strict Equality Check:* `work_escrow::attach_observation` enforces:
     $$\text{observation.roi\_hash} == \text{job.roi\_hash}$$
     Any coordinate discrepancy results in `Error::RoiHashMismatch`.
- **Residual Risk:** The farmer must verify that the ROI coordinates correspond to the intended clearing zone during job creation.

---

### Vector 10: Camera Displacement, Wind Drift & Lens Obstruction
- **Attack Mechanic:** Wind gusts, animal interference, or tractor vibration knock the camera out of alignment, causing the fixed ROI to measure a different section of the field.
- **Severity:** Medium
- **Mitigation:**
  1. *ORB Feature Matching & Homography Check:* Attester A's quality gate matches ORB keypoints between baseline and completion frames.
  2. *Translation Drift Bound:* The estimated affine translation vector must satisfy $\sqrt{\Delta x^2 + \Delta y^2} \le 20\text{ pixels}$. Larger shifts trigger `CAMERA_MOVED` rejection.
  3. *Inlier Ratio:* RANSAC homography inlier ratio must exceed 35%.
  4. *Lens Obstruction / Blur:* Mud splatters or spiderwebs cause image defocus, triggering Laplacian variance rejection (`BLURRED`).
- **Residual Risk:** Gradual camera creep of 1–2 pixels per week might accumulate unnoticed without periodic recalibration.

---

### Vector 11: Farmer & Worker Collusion Against Retainage / Arbiter
- **Attack Mechanic:** A farmer and worker conspire to extract escrowed funds or bypass the retainage delay.
- **Severity:** Low
- **Mitigation:**
  1. *Escrowed Capital Lockup:* The funds locked in escrow originate from the farmer. Collusion between farmer and worker does not siphon third-party funds; they can only reclaim their own deposited capital.
  2. *Arbiter Neutrality:* The arbiter has zero claim on escrowed principal; they can only split funds between farmer and worker (`resolve_dispute(worker_amount, farmer_amount)`).
- **Residual Risk:** Negligible for bilateral escrow.

---

### Vector 12: Arbiter Inactivity, Bribery, or Abandonment
- **Attack Mechanic:** A dispute is raised, freezing funds in `Disputed`. The assigned arbiter goes offline, loses their private key, or demands a bribe to release funds.
- **Severity:** High
- **Mitigation:**
  1. *Timed Arbiter Resolution Window:* Every dispute records `disputed_at` timestamp.
  2. *Farmer Timeout Reclaim:* If the arbiter fails to execute `resolve_dispute` within `DEFAULT_ARBITER_TIMEOUT_SECS` (604,800 seconds = 7 days), the farmer can invoke:
     $$\text{work\_escrow::reclaim\_disputed\_timeout(job\_id)}$$
     which automatically refunds remaining unreleased funds to the farmer and transitions the job to `Settled`.
- **Residual Risk:** A malicious arbiter who acts before the 7-day timeout could rule unfairly. Arbiters must be trusted or chosen via multi-sig.

---

## 4. Legal & Privacy Considerations

1. **Agricultural Worker Surveillance:**
   - Cameras are fixed-mount with low downward angles targeting agricultural beds, paths, and drainage channels.
   - Attester quality gates reject frames with high human presence or face close-ups.
2. **Bystander Privacy:**
   - Edge devices do not stream continuous video. They operate on episodic, challenge-gated single frame triggers.
   - No biometric identifiers or facial recognition models exist in the repository or pipeline.
3. **Data Protection (GDPR / CCPA):**
   - On-chain data is limited to cryptographic hashes, Ed25519 public keys, timestamps, and numerical basis points.
   - No raw imagery or personally identifiable information (PII) is stored on the Stellar ledger.

---

## 5. Summary Matrix

| Threat Vector | Attack Mechanism | Primary Layer | Mitigation Mechanism | Residual Risk Level |
| :--- | :--- | :---: | :--- | :---: |
| **1. Screen Replay** | Showing digital photo of clean bed | Attester / Contract | Challenge freshness + blur check + challenge window | Low |
| **2. Frame Replay** | Submitting pre-recorded signed frame | Contract | 16-byte fresh PRNG challenge + monotonic counter | Negligible |
| **3. Staging** | Plastic weeds or green spray paint | Escrow / Attester | Follow-up observation + retainage + spectral drift | Low |
| **4. Mulching / Tarps**| Covering weeds with plastic/cardboard | Escrow / Farmer | Ground color profile + follow-up delay + arbiter | Medium |
| **5. Shoot Mowing** | Cutting tops, leaving roots intact | Escrow | **Retainage lockup + follow-up regrowth check** | Low |
| **6. Sun Washout** | Specular sunlight masking green | Attester | Normalized ExG + CIELAB $a^*$ + exposure bounds | Low |
| **7. Key Theft** | Dumping ESP32 flash via UART | Firmware / Registry| Admin revocation + secure boot / flash encryption | Medium |
| **8. Attester Collusion**| Fake analysis reports | Registry / Verifier| Dual quorum + distinct family IDs + `pow-verify`| Low |
| **9. ROI Tampering** | Changing evaluation coordinates | Escrow | Canonical JSON + SHA-256 hash pinning on-chain | Negligible |
| **10. Camera Shift**| Wind or animal knocked tripod | Attester | ORB feature matching + translation drift bound | Low |
| **11. Collusion** | Parties trying to drain pool | Escrow | Capital-bounded escrow (only farmer's money) | Negligible |
| **12. Arbiter Freeze**| Arbiter disappears during dispute | Escrow | 7-day dispute timeout with farmer reclaim | Low |
