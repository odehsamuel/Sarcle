"""Attester A: Flask Service for Evidence Ingestion and CV Analysis.

Endpoints:
- POST /rois
- GET /rois/<roi_hash>
- GET /challenge
- POST /observations
- GET /images/<sha256>
- GET /health
"""

import hashlib
import json
import logging
import os
import struct
import sys
from flask import Flask, jsonify, request, send_file

# Add project root and tools to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

from analyzer import analyze_green_cover, compute_analyzer_hash
from ed25519_compact import checkvalid
from quality_gates import QualityGateFailure, run_quality_gates
from tools.chain_client import ChainClient

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("attester-a")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB limit

STORAGE_DIR = os.path.join(os.path.dirname(__file__), "storage")
IMAGES_DIR = os.path.join(STORAGE_DIR, "images")
ROIS_DIR = os.path.join(STORAGE_DIR, "rois")
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(ROIS_DIR, exist_ok=True)

# Initialize chain client (mock by default for clean test runs)
chain = ChainClient(mode="mock")

ATTESTER_ADDR = os.environ.get("ATTESTER_A_PUBLIC_KEY", "G_ATTESTER_A")
chain.registry_mock.add_attester(chain.admin, ATTESTER_ADDR)

# Pre-allowlist analyzer in registry
analyzer_hash = compute_analyzer_hash()
chain.registry_mock.allow_analyzer(
    chain.admin, analyzer_hash, metric_id=1, family_id=1
)


@app.route("/health", methods=["GET"])
def health():
    return jsonify(
        {
            "status": "healthy",
            "service": "attester-a",
            "metric_id": 1,
            "analyzer_hash_hex": analyzer_hash.hex(),
        }
    )


@app.route("/rois", methods=["POST"])
def register_roi():
    try:
        data = request.get_json(force=True)
        if not data or "points" not in data:
            return jsonify({"error": "Missing points array in JSON"}), 400

        # Enforce canonical format: 4 decimal places, strict alphabetical order
        points = []
        for p in data["points"]:
            x = round(float(p["x"]), 4)
            y = round(float(p["y"]), 4)
            points.append({"x": x, "y": y})

        canonical_obj = {
            "name": data.get("name", "roi"),
            "points": [
                {"x": f"{p['x']:.4f}", "y": f"{p['y']:.4f}"} for p in points
            ],
            "version": 1,
        }
        canonical_bytes = json.dumps(
            canonical_obj, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        roi_hash = hashlib.sha256(canonical_bytes).digest()
        roi_hash_hex = roi_hash.hex()

        # Persist to disk
        roi_file = os.path.join(ROIS_DIR, f"{roi_hash_hex}.json")
        with open(roi_file, "wb") as f:
            f.write(canonical_bytes)

        return (
            jsonify(
                {
                    "roi_hash_hex": roi_hash_hex,
                    "canonical_json": canonical_obj,
                    "points_count": len(points),
                }
            ),
            201,
        )
    except Exception as e:
        logger.error(f"Error registering ROI: {e}")
        return jsonify({"error": str(e)}), 400


@app.route("/rois/<roi_hash_hex>", methods=["GET"])
def get_roi(roi_hash_hex):
    roi_file = os.path.join(ROIS_DIR, f"{roi_hash_hex}.json")
    if not os.path.exists(roi_file):
        return jsonify({"error": "ROI not found"}), 404
    with open(roi_file, "r", encoding="utf-8") as f:
        return jsonify(json.load(f))


@app.route("/challenge", methods=["GET"])
def get_challenge():
    try:
        job_ref = int(request.args.get("job_ref", 0))
        kind = int(request.args.get("kind", 0))
        device_id_hex = request.args.get("device_id")
        if not device_id_hex:
            return jsonify({"error": "device_id is required"}), 400

        device_id = bytes.fromhex(device_id_hex)

        # Auto-register device in mock if not present
        if device_id not in chain.registry_mock.devices:
            chain.registry_mock.register_device(chain.admin, device_id)

        challenge = chain.request_challenge(
            ATTESTER_ADDR, job_ref, device_id, kind
        )
        return jsonify(
            {
                "challenge_hex": challenge.hex(),
                "job_ref": job_ref,
                "kind": kind,
                "device_id_hex": device_id_hex,
            }
        )
    except Exception as e:
        logger.error(f"Error requesting challenge: {e}")
        return jsonify({"error": str(e)}), 400


@app.route("/observations", methods=["POST"])
def submit_observation():
    try:
        # Accept multipart form or JSON
        if "image" in request.files:
            image_file = request.files["image"]
            image_bytes = image_file.read()
            raw_message_hex = request.form.get("raw_message_hex")
            signature_hex = request.form.get("signature_hex")
            roi_hash_hex = request.form.get("roi_hash_hex")
            prev_image_hash_hex = request.form.get("prev_image_hash_hex")
        else:
            data = request.get_json(force=True)
            image_bytes = bytes.fromhex(data["image_hex"])
            raw_message_hex = data["raw_message_hex"]
            signature_hex = data["signature_hex"]
            roi_hash_hex = data["roi_hash_hex"]
            prev_image_hash_hex = data.get("prev_image_hash_hex")

        if not (raw_message_hex and signature_hex and roi_hash_hex):
            return jsonify({"error": "Missing required fields"}), 400

        raw_msg = bytes.fromhex(raw_message_hex)
        sig = bytes.fromhex(signature_hex)
        roi_hash = bytes.fromhex(roi_hash_hex)

        if len(raw_msg) != 115:
            return (
                jsonify(
                    {"error": f"Message must be 115 bytes, got {len(raw_msg)}"}
                ),
                400,
            )

        # Unpack 115-byte message fields
        domain_tag = raw_msg[0:10]
        device_id = raw_msg[10:42]
        job_ref = struct.unpack(">Q", raw_msg[42:50])[0]
        kind = raw_msg[50]
        counter = struct.unpack(">Q", raw_msg[51:59])[0]
        timestamp = struct.unpack(">Q", raw_msg[59:67])[0]
        challenge = raw_msg[67:83]
        msg_image_sha256 = raw_msg[83:115]

        # 1. Local verification: Check image digest
        actual_image_sha256 = hashlib.sha256(image_bytes).digest()
        if actual_image_sha256 != msg_image_sha256:
            return (
                jsonify(
                    {
                        "error": "IMAGE_HASH_MISMATCH",
                        "message": "SHA-256 of JPEG does not match signed message payload",
                        "expected": msg_image_sha256.hex(),
                        "actual": actual_image_sha256.hex(),
                    }
                ),
                422,
            )

        # 2. Local verification: Check Ed25519 signature
        if not checkvalid(sig, raw_msg, device_id):
            return (
                jsonify(
                    {
                        "error": "INVALID_SIGNATURE",
                        "message": "Device Ed25519 signature verification failed locally",
                    }
                ),
                422,
            )

        # 3. Load ROI Polygon
        roi_file = os.path.join(ROIS_DIR, f"{roi_hash_hex}.json")
        if not os.path.exists(roi_file):
            return (
                jsonify(
                    {
                        "error": "ROI_NOT_FOUND",
                        "message": f"ROI {roi_hash_hex} not registered with attester",
                    }
                ),
                404,
            )

        with open(roi_file, "r", encoding="utf-8") as f:
            roi_data = json.load(f)
        roi_points = [
            {"x": float(p["x"]), "y": float(p["y"])}
            for p in roi_data["points"]
        ]

        # 4. Run Quality Gates
        prev_jpeg = None
        if prev_image_hash_hex:
            prev_file = os.path.join(IMAGES_DIR, f"{prev_image_hash_hex}.jpg")
            if os.path.exists(prev_file):
                with open(prev_file, "rb") as pf:
                    prev_jpeg = pf.read()

        try:
            run_quality_gates(image_bytes, roi_points, prev_jpeg=prev_jpeg)
        except QualityGateFailure as qg:
            logger.warning(
                f"Quality gate rejected frame: {qg.reason} ({qg.details})"
            )
            return (
                jsonify(
                    {
                        "error": "QUALITY_GATE_REJECTED",
                        "reason": qg.reason,
                        "details": qg.details,
                    }
                ),
                422,
            )

        # 5. Run Classical CV Analyzer
        cover_bps, _, an_hash = analyze_green_cover(image_bytes, roi_points)

        # 6. Submit to Evidence Registry on-chain
        obs_id = chain.submit_observation(
            attester_addr=ATTESTER_ADDR,
            job_ref=job_ref,
            kind=kind,
            image_hash=actual_image_sha256,
            roi_hash=roi_hash,
            metric_id=1,
            challenge=challenge,
            counter=counter,
            timestamp=timestamp,
            signature=sig,
            analyzer_hash=an_hash,
            value_bps=cover_bps,
        )

        # 7. Persist Image to disk
        img_out = os.path.join(IMAGES_DIR, f"{actual_image_sha256.hex()}.jpg")
        with open(img_out, "wb") as f:
            f.write(image_bytes)

        logger.info(
            f"Successfully recorded observation {obs_id} for job {job_ref} (cover: {cover_bps} bps)"
        )
        return (
            jsonify(
                {
                    "obs_id": obs_id,
                    "job_ref": job_ref,
                    "kind": kind,
                    "cover_bps": cover_bps,
                    "analyzer_hash_hex": an_hash.hex(),
                    "image_sha256_hex": actual_image_sha256.hex(),
                    "status": "Submitted",
                }
            ),
            201,
        )

    except Exception as e:
        logger.error(f"Error submitting observation: {e}")
        return jsonify({"error": str(e)}), 400


@app.route("/images/<image_sha256_hex>", methods=["GET"])
def get_image(image_sha256_hex):
    img_path = os.path.join(IMAGES_DIR, f"{image_sha256_hex}.jpg")
    if not os.path.exists(img_path):
        return jsonify({"error": "Image not found"}), 404
    return send_file(img_path, mimetype="image/jpeg")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
