# Issues Seed: 20 Actionable Community Tasks

> **Status:** Open / Roadmap v0.2  
> **Repository:** Proof-of-Weeding (Stellar / Soroban)  
> **Instructions for Contributors:** Each issue below is fully specified with context, acceptance criteria, affected files, and complexity estimates. When taking on an issue, please comment on the GitHub tracker to avoid duplicate effort.

---

## 1. Rust Smart Contracts & Analyzers

### Issue #1: Add Batch Device Registration to `evidence_registry`
- **Component:** `contracts/evidence_registry`
- **Complexity:** `Medium` | **Priority:** `P1`
- **Context:** Currently, administrators must call `register_device` individually for every edge camera. Deploying a fleet of 50 cameras requires 50 separate transactions, causing unnecessary transaction overhead.
- **Affected Files:**
  - `contracts/evidence_registry/src/lib.rs`
  - `contracts/evidence_registry/src/test.rs`
- **Acceptance Criteria:**
  - Implement `register_devices(admin: Address, devices: Vec<DeviceId>)`.
  - Re-use internal registration helper to ensure identical event emission and TTL policy.
  - Add unit test verifying that registering 10 devices in a single call correctly updates persistent storage and emits 10 events.

---

### Issue #2: Support Multi-Milestone Clearing Jobs in `work_escrow`
- **Component:** `contracts/work_escrow`
- **Complexity:** `High` | **Priority:** `P2`
- **Context:** Large acreage projects require dividing a field into multiple stages (e.g. Zone 1, Zone 2, Zone 3) with progressive fund disbursements rather than an all-or-nothing completion release.
- **Affected Files:**
  - `contracts/work_escrow/src/types.rs`
  - `contracts/work_escrow/src/lib.rs`
  - `contracts/work_escrow/src/storage.rs`
- **Acceptance Criteria:**
  - Extend `Job` to accept a vector of `Milestone { roi_hash, amount_fraction_bps, completed: bool }`.
  - Modify `attach_observation` to accept a `milestone_index: u32`.
  - Payout proportional amount while preserving retainage calculation until the final milestone is reached.

---

### Issue #3: Implement Attester Slashing / Collateral Penalization in `evidence_registry`
- **Component:** `contracts/evidence_registry`
- **Complexity:** `High` | **Priority:** `P2`
- **Context:** In a decentralized attester network, attesters should lock token collateral. If an attester repeatedly produces divergent or fraudulent analyses, their stake should be slashed.
- **Affected Files:**
  - `contracts/evidence_registry/src/types.rs`
  - `contracts/evidence_registry/src/lib.rs`
- **Acceptance Criteria:**
  - Allow attesters to deposit collateral during `add_attester`.
  - Track divergence count per attester. If divergence exceeds a threshold, freeze attester permissions and burn or redistribute 10% of their stake.

---

### Issue #4: Emit Structured Events for Arbiter Dispute Resolution
- **Component:** `contracts/work_escrow`
- **Complexity:** `Trivial` | **Priority:** `P1`
- **Context:** `resolve_dispute` currently emits a generic event without explicitly detailing the exact amounts split between farmer and worker.
- **Affected Files:**
  - `contracts/work_escrow/src/events.rs`
  - `contracts/work_escrow/src/lib.rs`
- **Acceptance Criteria:**
  - Define `DisputeResolvedEvent { job_id: u64, arbiter: Address, worker_payout: i128, farmer_refund: i128 }`.
  - Update `resolve_dispute` to emit this event and add a corresponding test in `contracts/work_escrow/src/test.rs`.

---

### Issue #5: Pure Rust JPEG Decoder for Attester B Without System Dependencies
- **Component:** `attester-b`
- **Complexity:** `Medium` | **Priority:** `P1`
- **Context:** Attester B should run cleanly in minimal WebAssembly environments (e.g., Soroban host or WasmEdge) without requiring C-based `libjpeg-turbo` or operating system libraries.
- **Affected Files:**
  - `attester-b/Cargo.toml`
  - `attester-b/src/main.rs`
- **Acceptance Criteria:**
  - Integrate a pure-Rust `zune-jpeg` or `jpeg-decoder` crate into `attester-b`.
  - Ensure zero unsafe blocks and clean compilation to `wasm32-unknown-unknown`.
  - Output exact same basis points calculation as native desktop build.

---

## 2. Python Attester Services, Computer Vision & Tools

### Issue #6: Implement Solar Shadow Segmentation in Excess Green Analyzer
- **Component:** `attester-a`
- **Complexity:** `High` | **Priority:** `P1`
- **Context:** Cloud shadows or nearby trees cast deep shadows across the ROI, altering color chromaticity and causing Otsu thresholding to misidentify shaded soil as weed canopy.
- **Affected Files:**
  - `attester-a/analyzer.py`
  - `tests/test_attester_a.py`
- **Acceptance Criteria:**
  - Implement a luminance mask ($Y < 40$ in YCrCb or $V < 0.2$ in HSV) to isolate shadowed regions.
  - Apply adaptive histogram equalization (CLAHE) specifically within the shadow mask before computing chromatic Excess Green.
  - Verify that shadow presence does not bias ground-truth synthetic tests by more than 300 bps.

---

### Issue #7: Add Prometheus Metrics Endpoint to Attester A
- **Component:** `attester-a`
- **Complexity:** `Trivial` | **Priority:** `P2`
- **Context:** Production node operators need real-time observability into incoming observation processing times, quality gate rejection rates, and contract submission latency.
- **Affected Files:**
  - `attester-a/app.py`
  - `attester-a/requirements.txt`
- **Acceptance Criteria:**
  - Add `/metrics` endpoint returning Prometheus-compatible text metrics.
  - Track: `attester_frames_received_total`, `attester_quality_rejections_total{reason=...}`, `attester_analysis_duration_seconds`.

---

### Issue #8: Procedural Generation of Field Obstacles in Synthetic Scenes
- **Component:** `tools/synthetic-scenes`
- **Complexity:** `Medium` | **Priority:** `P1`
- **Context:** Real agricultural beds contain non-soil elements such as rocks, drip irrigation tubing, dry straw mulch, and footprints.
- **Affected Files:**
  - `tools/synthetic-scenes/generate.py`
- **Acceptance Criteria:**
  - Add procedural generation routines for grey stones (elliptical Voronoi patches) and black drip tape (continuous spline lines).
  - Ensure obstacles are excluded from the ground-truth weed mask calculation.
  - Confirm analyzer divergence between Attester A and Attester B remains under 500 bps on cluttered scenes.

---

### Issue #9: Variable Network Latency Simulator in Device Simulator
- **Component:** `tools/device-simulator`
- **Complexity:** `Trivial` | **Priority:** `P2`
- **Context:** Rural cellular connections (GPRS/LTE-M) experience high jitter, packet loss, and frequent dropped connections.
- **Affected Files:**
  - `tools/device-simulator/simulate.py`
- **Acceptance Criteria:**
  - Add `--jitter-ms` and `--loss-rate` CLI flags.
  - Implement retry-with-backoff logic when uploading signed frames to the attester endpoint.

---

### Issue #10: JSON Output Flag for Public Verifier CLI (`pow-verify`)
- **Component:** `tools/pow-verify`
- **Complexity:** `Trivial` | **Priority:** `P1`
- **Context:** Automated CI pipelines and audit bots require machine-readable JSON output from `pow-verify` instead of terminal text.
- **Affected Files:**
  - `tools/pow-verify/verify.py`
- **Acceptance Criteria:**
  - Add `--json` flag to `tools/pow-verify/verify.py`.
  - When specified, suppress ASCII banners and emit a single valid JSON object containing per-observation verification statuses, recomputed bps, and exit code 0 (PASS) or 1 (FAIL).

---

### Issue #11: Automated Hyperparameter Calibration Script
- **Component:** `tools/calibrate_analyzers.py`
- **Complexity:** `Medium` | **Priority:** `P1`
- **Context:** The current CIELAB $a^*$ threshold was calibrated by manual step sweep. An automated optimizer should discover optimal thresholds across diverse soil types.
- **Affected Files:**
  - `tools/calibrate_analyzers.py`
- **Acceptance Criteria:**
  - Implement grid search / Brent's method to find the optimal fixed-point threshold minimizing mean absolute error against Attester A across 100 scenes.
  - Save output parameters directly into `docs/calibration-report.json`.

---

## 3. Firmware & Edge Device (ESP32-CAM)

### Issue #12: Enable NVS Flash Encryption for Monotonic Counter Protection
- **Component:** `firmware/esp32cam`
- **Complexity:** `High` | **Priority:** `P0`
- **Context:** Monotonic sequence counters prevent replay attacks. If an attacker can dump NVS flash, reset the counter to zero, and reflash, replay protection is weakened.
- **Affected Files:**
  - `firmware/esp32cam/platformio.ini`
  - `firmware/esp32cam/src/main.cpp`
- **Acceptance Criteria:**
  - Configure `nvs_flash_secure_init()` using ESP-IDF flash encryption partition.
  - Provide documentation in `firmware/esp32cam/README.md` detailing eFuse burning procedures for production hardware.

---

### Issue #13: Deep Sleep Duty Cycling with RTC Wakeup
- **Component:** `firmware/esp32cam`
- **Complexity:** `Medium` | **Priority:** `P1`
- **Context:** Agricultural cameras run on small solar panels and 18650 Li-ion cells. Keeping the Wi-Fi modem and OV2640 sensor powered continuously depletes the battery within hours.
- **Affected Files:**
  - `firmware/esp32cam/src/main.cpp`
- **Acceptance Criteria:**
  - Implement `esp_deep_sleep_start()` between scheduled capture intervals.
  - Power down camera sensor rails via GPIO pin during sleep.
  - Average sleep power consumption must be $< 1.5\text{ mA}$.

---

### Issue #14: LED Flash Pulse Synchronization for Night / Shadow Mitigation
- **Component:** `firmware/esp32cam`
- **Complexity:** `Trivial` | **Priority:** `P2`
- **Context:** Extreme low-light conditions fail the exposure quality gate. Triggering the onboard high-intensity LED flash stabilizes scene luminance.
- **Affected Files:**
  - `firmware/esp32cam/src/main.cpp`
- **Acceptance Criteria:**
  - Enable onboard GPIO 4 (LED flash) for 150ms during frame capture.
  - Ensure flash shuts down immediately after frame buffer readout to prevent overheating.

---

### Issue #15: Captive Portal Wi-Fi Provisioning
- **Component:** `firmware/esp32cam`
- **Complexity:** `Medium` | **Priority:** `P2`
- **Context:** Hardcoding Wi-Fi credentials in header files is insecure and inconvenient for field deployment.
- **Affected Files:**
  - `firmware/esp32cam/src/main.cpp`
  - `firmware/esp32cam/platformio.ini`
- **Acceptance Criteria:**
  - If Wi-Fi fails to connect within 30 seconds, spawn an Access Point (`PoW-Camera-Setup`).
  - Serve a lightweight configuration webpage to submit local Wi-Fi SSID and passkey, saving them to NVS.

---

## 4. Frontend & User Interface (React / Vite / TypeScript)

### Issue #16: Interactive Canvas Polygon ROI Editor
- **Component:** `dashboard`
- **Complexity:** `High` | **Priority:** `P1`
- **Context:** Currently, job creators must manually paste JSON coordinates for the target polygon. A point-and-click visual canvas editor is essential for usability.
- **Affected Files:**
  - `dashboard/src/components/CreateJob.tsx`
  - `dashboard/src/components/RoiEditor.tsx` (new)
- **Acceptance Criteria:**
  - Render a sample field image on an HTML5 `<canvas>`.
  - Allow users to click vertices to form an arbitrary polygon.
  - Export coordinates in strict `docs/spec/roi-format.md` canonical format with 6-decimal precision and automatic SHA-256 calculation.

---

### Issue #17: Multi-Network Switcher (Testnet / Futurenet / Local Standalone)
- **Component:** `dashboard`
- **Complexity:** `Medium` | **Priority:** `P1`
- **Context:** Developers need to toggle between Stellar Testnet, Futurenet, and local `stellar-cli container` test environments without editing `.env`.
- **Affected Files:**
  - `dashboard/src/App.tsx`
  - `dashboard/src/utils/stellar.ts`
- **Acceptance Criteria:**
  - Add network dropdown in navigation bar.
  - Automatically update RPC URL and network passphrase in Freighter connection requests.

---

### Issue #18: Live WebSocket Feed for Observation Consensus
- **Component:** `dashboard`
- **Complexity:** `Medium` | **Priority:** `P2`
- **Context:** When a completion frame is uploaded, users must currently refresh the page to see if Attester A and Attester B have both signed.
- **Affected Files:**
  - `dashboard/src/components/JobDetail.tsx`
- **Acceptance Criteria:**
  - Connect to Attester A's server-sent event (SSE) or WebSocket endpoint.
  - Visually animate progress bar when Attester A submits, then Attester B submits, culminating in the `Accepted` green checkmark.

---

### Issue #19: Interactive Image Diff Slider for Baseline vs Completion
- **Component:** `dashboard`
- **Complexity:** `Medium` | **Priority:** `P2`
- **Context:** Farmers and arbiters need to visually inspect the exact ground difference between baseline and completion imagery before deciding on dispute action.
- **Affected Files:**
  - `dashboard/src/components/JobDetail.tsx`
  - `dashboard/src/components/ImageComparisonSlider.tsx` (new)
- **Acceptance Criteria:**
  - Implement a split-pane before/after comparison slider over the ROI area.
  - Highlight the canonical ROI polygon outline over both images.

---

### Issue #20: Audit Trail CSV / JSON Exporter
- **Component:** `dashboard`
- **Complexity:** `Trivial` | **Priority:** `P2`
- **Context:** Agricultural compliance auditors require downloadable proof bundles containing the contract address, device public key, image SHA-256 hashes, and timestamp signatures.
- **Affected Files:**
  - `dashboard/src/components/JobDetail.tsx`
- **Acceptance Criteria:**
  - Add "Export Audit Bundle" button.
  - Generate a downloadable `.zip` or `.json` file containing the job ledger state, observation records, and verification commands.
