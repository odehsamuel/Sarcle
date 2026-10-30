#!/usr/bin/env python3
"""Solar Power Budget & Battery Autonomy Numerical Simulator.

Simulates energy harvesting from solar MPPT controllers against edge camera
power duty cycling to evaluate year-round autonomy and brownout safety.
"""

import argparse
import json
import math
import sys
from typing import Dict, List, Tuple


class SolarPowerSimulator:
    def __init__(
        self,
        panel_watts: float = 3.0,
        mppt_efficiency: float = 0.92,
        battery_mah: float = 1500.0,
        battery_voltage: float = 3.2,  # LiFePO4 nominal
        sleep_current_ma: float = 0.015,
        capture_current_ma: float = 120.0,
        capture_time_sec: float = 3.0,
        cellular_current_ma: float = 260.0,
        cellular_time_sec: float = 9.0,
        captures_per_day: int = 4,
    ):
        self.panel_watts = panel_watts
        self.mppt_efficiency = mppt_efficiency
        self.battery_mah = battery_mah
        self.battery_voltage = battery_voltage
        self.battery_mwh = battery_mah * battery_voltage

        self.sleep_ma = sleep_current_ma
        self.capture_ma = capture_current_ma
        self.capture_sec = capture_time_sec
        self.cellular_ma = cellular_current_ma
        self.cellular_sec = cellular_time_sec
        self.captures_per_day = captures_per_day

    def calculate_daily_consumption(self) -> Dict[str, float]:
        """Compute energy consumption per 24-hour cycle."""
        active_time_sec = self.captures_per_day * (self.capture_sec + self.cellular_sec)
        sleep_time_sec = 86400 - active_time_sec

        # Energy in milliamp-seconds (mAs)
        active_mas = self.captures_per_day * (
            (self.capture_ma * self.capture_sec)
            + (self.cellular_ma * self.cellular_sec)
        )
        sleep_mas = self.sleep_ma * sleep_time_sec
        total_mas = active_mas + sleep_mas

        daily_mah = total_mas / 3600.0
        daily_mwh = daily_mah * self.battery_voltage
        average_current_ma = daily_mah / 24.0

        return {
            "daily_consumption_mah": round(daily_mah, 3),
            "daily_consumption_mwh": round(daily_mwh, 3),
            "average_current_ma": round(average_current_ma, 4),
            "active_seconds_per_day": active_time_sec,
        }

    def simulate_day_harvest(
        self, peak_sun_hours: float = 4.5, cloud_factor: float = 1.0
    ) -> float:
        """Calculate solar energy harvested in mWh for a single day."""
        # Wh = Panel Watts * Peak Sun Hours * MPPT Efficiency * Cloud Factor
        harvested_wh = self.panel_watts * peak_sun_hours * self.mppt_efficiency * cloud_factor
        return harvested_wh * 1000.0  # Convert to mWh

    def simulate_consecutive_cloud_days(
        self, cloud_days: int = 7, initial_soc: float = 1.0
    ) -> Dict[str, any]:
        """Simulate battery drain across consecutive zero/low-solar days."""
        consumption = self.calculate_daily_consumption()
        daily_drain_mwh = consumption["daily_consumption_mwh"]

        current_energy_mwh = self.battery_mwh * initial_soc
        history = []
        brownout_occurred = False
        brownout_day = -1

        for day in range(1, cloud_days + 1):
            # Heavy overcast: ~8% of standard sun
            harvest_mwh = self.simulate_day_harvest(peak_sun_hours=1.0, cloud_factor=0.08)
            net_change = harvest_mwh - daily_drain_mwh
            current_energy_mwh += net_change

            if current_energy_mwh > self.battery_mwh:
                current_energy_mwh = self.battery_mwh

            soc = max(0.0, current_energy_mwh / self.battery_mwh)
            history.append({
                "day": day,
                "harvest_mwh": round(harvest_mwh, 2),
                "drain_mwh": round(daily_drain_mwh, 2),
                "soc_percent": round(soc * 100.0, 1),
            })

            if soc <= 0.05 and not brownout_occurred:
                brownout_occurred = True
                brownout_day = day

        autonomy_days_zero_sun = self.battery_mwh * 0.95 / daily_drain_mwh

        return {
            "battery_capacity_mah": self.battery_mah,
            "battery_nominal_voltage": self.battery_voltage,
            "battery_total_mwh": round(self.battery_mwh, 2),
            "daily_consumption": consumption,
            "autonomy_days_zero_sun": round(autonomy_days_zero_sun, 1),
            "brownout_occurred_during_streak": brownout_occurred,
            "brownout_day": brownout_day,
            "streak_days_simulated": cloud_days,
            "final_soc_percent": history[-1]["soc_percent"],
            "daily_trace": history,
        }


def main():
    parser = argparse.ArgumentParser(description="Solar Autonomy Simulator for Edge Camera")
    parser.add_argument("--panel-watts", type=float, default=3.0)
    parser.add_argument("--battery-mah", type=float, default=1500.0)
    parser.add_argument("--captures-per-day", type=int, default=4)
    parser.add_argument("--cloud-streak", type=int, default=14)
    parser.add_argument("--json-output", type=str, default=None)

    args = parser.parse_args()

    sim = SolarPowerSimulator(
        panel_watts=args.panel_watts,
        battery_mah=args.battery_mah,
        captures_per_day=args.captures_per_day,
    )

    res = sim.simulate_consecutive_cloud_days(cloud_days=args.cloud_streak)

    print("==================================================")
    print("PROOF-OF-WEEDING SOLAR AUTONOMY SIMULATOR")
    print("==================================================")
    print(f"[*] Panel Rating:        {args.panel_watts} Watts")
    print(f"[*] Battery Capacity:    {args.battery_mah} mAh ({res['battery_total_mwh']} mWh)")
    print(f"[*] Captures per day:    {args.captures_per_day} frames")
    print(f"[*] Daily Consumption:   {res['daily_consumption']['daily_consumption_mah']} mAh/day")
    print(f"[*] Average Current:     {res['daily_consumption']['average_current_ma']} mA (< 1.5 mA target)")
    print(f"[*] Zero-Sun Autonomy:   {res['autonomy_days_zero_sun']} days")
    print(f"[*] {args.cloud_streak}-Day Streak Final SoC: {res['final_soc_percent']}%")
    print(f"[*] Brownout Observed:   {res['brownout_occurred_during_streak']}")

    if args.json_output:
        with open(args.json_output, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2)
        print(f"[+] Saved simulation results to {args.json_output}")


if __name__ == "__main__":
    main()

