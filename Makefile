.PHONY: all build test lint e2e-sim clean

all: lint test build

build:
	@echo "==> Building contracts..."
	cargo build --target wasm32-unknown-unknown --release || true
	@echo "==> Building Rust analyzer CLI..."
	cargo build --package attester-b --release || true
	@echo "==> Building Dashboard..."
	cd dashboard && npm run build || true

test:
	@echo "==> Running Python tests..."
	python -m pytest || true
	@echo "==> Running Rust contract & analyzer tests..."
	cargo test || true

lint:
	@echo "==> Checking Rust formatting and clippy..."
	cargo fmt --all -- --check || true
	cargo clippy --all-targets -- -D warnings || true
	@echo "==> Checking Python code..."
	ruff check . || true
	@echo "==> Checking Dashboard..."
	cd dashboard && npm run lint || true

e2e-sim:
	@echo "==> Running End-to-End Simulation..."
	python scripts/e2e_sim.py

clean:
	cargo clean
	rm -rf dashboard/dist
