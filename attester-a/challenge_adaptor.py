"""Network Latency & Challenge Window Adaptation Engine.

Monitors edge device round-trip cellular latencies and adjusts challenge TTL buffers,
retry horizons, and clock skew tolerances for remote rural deployments.
"""

import time
from typing import Dict, Optional


class ChallengeWindowAdaptor:
    def __init__(
        self,
        base_challenge_ttl_sec: int = 300,
        base_timestamp_tolerance_sec: int = 60,
        ema_alpha: float = 0.25,
    ):
        self.base_ttl = base_challenge_ttl_sec
        self.base_tolerance = base_timestamp_tolerance_sec
        self.alpha = ema_alpha
        # device_id_hex -> {rtt_ema_sec, last_updated, sample_count, failed_attempts}
        self.device_metrics: Dict[str, Dict] = {}

    def record_network_round_trip(
        self, device_id_hex: str, rtt_seconds: float, success: bool = True
    ) -> Dict[str, float]:
        """Record an observed network round-trip time sample for a device."""
        if device_id_hex not in self.device_metrics:
            self.device_metrics[device_id_hex] = {
                "rtt_ema_sec": rtt_seconds,
                "rtt_variance": 0.0,
                "sample_count": 1,
                "failed_attempts": 0 if success else 1,
                "last_seen": time.time(),
            }
        else:
            rec = self.device_metrics[device_id_hex]
            old_ema = rec["rtt_ema_sec"]
            # Update EMA
            new_ema = self.alpha * rtt_seconds + (1.0 - self.alpha) * old_ema
            # Variance update
            rec["rtt_variance"] = (1.0 - self.alpha) * (rec["rtt_variance"] + self.alpha * ((rtt_seconds - old_ema) ** 2))
            rec["rtt_ema_sec"] = new_ema
            rec["sample_count"] += 1
            rec["last_seen"] = time.time()
            if not success:
                rec["failed_attempts"] += 1
            else:
                rec["failed_attempts"] = max(0, rec["failed_attempts"] - 1)

        return self.get_device_latency_profile(device_id_hex)

    def get_device_latency_profile(self, device_id_hex: str) -> Dict[str, any]:
        """Retrieve telemetry metrics and dynamic adaptation parameters."""
        rec = self.device_metrics.get(
            device_id_hex,
            {
                "rtt_ema_sec": 5.0,  # Default assumption: 5-second rural cellular RTT
                "rtt_variance": 1.0,
                "sample_count": 0,
                "failed_attempts": 0,
            },
        )

        rtt = rec["rtt_ema_sec"]
        # Safety buffer: 4x RTT + 15 seconds upload transmission budget
        transmission_budget_sec = (4.0 * rtt) + 15.0

        # Suggested challenge TTL to request from registry
        adapted_ttl_sec = max(
            self.base_ttl,
            int(transmission_budget_sec + 60.0),
        )

        # Fraction of challenge TTL expected to be consumed by network
        ttl_consumption_fraction = min(1.0, transmission_budget_sec / float(adapted_ttl_sec))

        latency_risk = "LOW"
        if ttl_consumption_fraction > 0.60 or rec["failed_attempts"] >= 2:
            latency_risk = "HIGH"
        elif ttl_consumption_fraction > 0.35:
            latency_risk = "MODERATE"

        return {
            "device_id_hex": device_id_hex,
            "rtt_ema_sec": round(rtt, 2),
            "transmission_budget_sec": round(transmission_budget_sec, 2),
            "recommended_challenge_ttl_sec": adapted_ttl_sec,
            "ttl_consumption_fraction": round(ttl_consumption_fraction, 3),
            "latency_risk": latency_risk,
            "failed_attempts": rec["failed_attempts"],
        }

    def evaluate_challenge_freshness(
        self,
        device_id_hex: str,
        issued_at_timestamp: int,
        challenge_ttl_sec: int,
        current_timestamp: Optional[int] = None,
    ) -> Tuple[bool, Dict[str, any]]:
        """Determine whether the challenge remains fresh enough to accept a frame."""
        if current_timestamp is None:
            current_timestamp = int(time.time())

        elapsed_sec = current_timestamp - issued_at_timestamp
        remaining_sec = challenge_ttl_sec - elapsed_sec
        profile = self.get_device_latency_profile(device_id_hex)

        # Fresh if remaining TTL exceeds device upload budget
        is_fresh = remaining_sec > (profile["rtt_ema_sec"] + 5.0)

        diag = {
            "elapsed_sec": elapsed_sec,
            "remaining_sec": remaining_sec,
            "challenge_ttl_sec": challenge_ttl_sec,
            "is_fresh": is_fresh,
            **profile,
        }
        return is_fresh, diag
