# Contributing to Proof-of-Weeding

Thank you for your interest in contributing to Proof-of-Weeding! This project bridges physical edge sensing with Stellar/Soroban smart contract escrow.

---

## 1. Clean-Room & Integrity Guidelines

To maintain scientific rigor and clear intellectual property boundaries, all contributors must strictly adhere to our **Clean-Room Rules**:

1. **Zero External Imagery or Datasets:**
   - Do **NOT** import, commit, or link to external plant datasets (e.g. Kaggle, ImageNet, PlantDoc, or proprietary agricultural photos).
   - Every test scene must be generated procedurally using the in-repo generator ([`tools/synthetic-scenes/generate.py`](file:///c:/Users/USER/Projects/Sarcle/tools/synthetic-scenes/generate.py)).
2. **Zero Machine Learning Weights:**
   - Do **NOT** add neural network weights, `.pt`, `.onnx`, or pickled models.
   - All analyzers in this repository must use deterministic, classical computer vision algorithms behind defined metric interfaces.
3. **Zero Fabricated Claims or Numbers:**
   - Any accuracy or performance numbers reported in documentation must cite reproducible scripts in this repository and be explicitly labeled as **synthetic**.
   - If a feature is incomplete, mark it clearly as `TODO` or `STUB`.

---

## 2. Commit Message Standards

We enforce **Conventional Commits** (`v1.0.0`). All commit messages must follow the structure:

```
<type>(<scope>): <short description>
```

### Allowed Types
- `feat`: New feature or capability.
- `fix`: Bug fix.
- `test`: Adding or refactoring tests.
- `docs`: Documentation updates.
- `refactor`: Code reorganization without functional changes.
- `chore`: Build scripts, dependencies, or toolchain configuration.

### Common Scopes
- `spec`: Canonical observation, ROI, or metric specifications.
- `contracts`: Soroban Rust contracts (`evidence_registry`, `work_escrow`).
- `attester`: Attester A (Python) or Attester B (Rust).
- `firmware`: ESP32-CAM PlatformIO codebase.
- `dashboard`: React/Vite web interface.
- `tools`: Synthetic scenes, device simulator, or `pow-verify`.

---

## 3. Development Workflow & Testing

### Running Tests Locally

#### A. Python Test Suite (Specs, Mocks, Attesters, Quality Gates, Simulator)
```bash
python -m unittest discover tests
```
*All 18+ tests should pass in ~10 seconds.*

#### B. End-to-End Simulation Pipeline
```bash
python scripts/e2e_sim.py
```

#### C. Public Verification CLI Audit
```bash
python tools/pow-verify/verify.py --job-id 1 \
  --roi-file attester-a/storage/rois/084e1a3f688169af5cd3030c5dadf272006d94a4d6d1d7f5406d5a5daa764d04.json
```

#### D. Rust Smart Contracts (Soroban SDK)
```bash
cargo test --workspace
```

#### E. Frontend Dashboard
```bash
cd dashboard
npm install
npm run build
```

---

## 4. Picking Up an Issue

Ready to contribute? Check out [`docs/ISSUES_SEED.md`](file:///c:/Users/USER/Projects/Sarcle/docs/ISSUES_SEED.md) for 20 fully specified tasks across Rust, Python, Firmware, and TypeScript.

When you're ready:
1. Open a discussion or comment on the relevant GitHub issue to reserve it.
2. Fork the repository and create a descriptive branch: `git checkout -b feat/my-new-feature`.
3. Ensure all automated tests pass and any new functionality includes unit tests.
4. Open a Pull Request referencing the issue number.
