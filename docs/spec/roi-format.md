# Canonical Region-of-Interest (ROI) Specification

This specification defines the canonical representation for defining target vegetation clearing zones within a camera's fixed field of view.

---

## 1. Design Overview

To ensure that smart contracts remain agnostic of large geometric coordinates while remaining strictly verifiable:
1. The full polygon definition is stored **off-chain** by attester services and the client dashboard.
2. The smart contracts (`evidence_registry` and `work_escrow`) store only the 32-byte cryptographic digest:
   $$\text{roi\_hash} = \text{SHA-256}(\text{Canonical-JSON-Bytes})$$
3. When analyzing observations, both Attester A and Attester B verify that $\text{SHA-256}(\text{roi\_bytes}) == \text{roi\_hash}$.

---

## 2. Canonical JSON Serialization Rules

To guarantee cross-platform cryptographic digest determinism across Python, Rust, JavaScript, and embedded C++:

1. **Normalized Coordinates**: Coordinates are normalized to $[0.0, 1.0]$ relative to the full sensor frame width and height ($0.0 \le x \le 1.0$, $0.0 \le y \le 1.0$), where $(0,0)$ is top-left and $(1,1)$ is bottom-right.
2. **Fixed Decimal Precision**: All coordinate floating-point numbers are formatted with exactly **4 decimal places** (e.g. `0.2500`, `1.0000`, `0.0000`).
3. **Fixed Key Order**: Keys must appear in strict alphabetical order:
   - Root object: `"name"`, `"points"`, `"version"`
   - Point object: `"x"`, `"y"`
4. **No Unnecessary Whitespace**: Canonical JSON contains zero whitespace outside quoted strings (no spaces after colons, no newlines, no indentation).
5. **Encoding**: UTF-8 without Byte Order Mark (BOM).

---

## 3. Schema & Canonical Example

### Schema Definition
```json
{
  "name": "string",
  "points": [
    {
      "x": "0.0000 to 1.0000",
      "y": "0.0000 to 1.0000"
    }
  ],
  "version": 1
}
```

### Canonical Byte-Stream Example (Single Line, No Spaces)
```json
{"name":"fallow_bed_north","points":[{"x":"0.1500","y":"0.2000"},{"x":"0.8500","y":"0.2000"},{"x":"0.8500","y":"0.8000"},{"x":"0.1500","y":"0.8000"}],"version":1}
```

### Validation Constraints
- **Minimum Vertices**: The polygon must contain at least 3 distinct non-collinear vertices ($N \ge 3$).
- **Non-Self-Intersecting**: The polygon perimeter must be simple and non-self-intersecting.
- **Minimum Enclosed Area**: Normalized enclosed polygon area must be at least $0.01$ (1% of frame area) and at most $0.98$ to prevent degenerate edge-clipping.
