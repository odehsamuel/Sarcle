# Justfile for Proof-of-Weeding

default:
    @just --list

# Run linter checks
lint:
    cargo fmt --all -- --check
    cargo clippy --all-targets -- -D warnings
    ruff check .
    cd dashboard && npm run lint

# Run all test suites
test:
    cargo test
    python -m pytest

# Build contracts and packages
build:
    cargo build --target wasm32-unknown-unknown --release
    cargo build --package attester-b --release
    cd dashboard && npm run build

# Run end-to-end simulation
e2e-sim:
    python scripts/e2e_sim.py
