"""Offline per-satellite link-state dataset exporter."""

from __future__ import annotations

import os
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple

import numpy as np

from .calculator import OrbitCalculator
from .strategies import GridDeltaStrategy


SEPARATOR = "-" * 60
LIGHT_SPEED_KM_PER_S = 299792.458

LinkKey = Tuple[int, int]
ProgressCallback = Callable[[int, int], bool]


class LinkDatasetExportCancelled(Exception):
    """Raised when a user cancels offline dataset export."""


@dataclass
class LinkDatasetExportResult:
    output_dir: str
    file_count: int
    time_slices: int


class RandomLinkFailureModel:
    """Per-link up-to-down process with blinking failure periods."""

    def __init__(
        self,
        *,
        enabled: bool,
        failure_probability: float,
        random_seed: int,
        min_down_slices: int = 2,
        max_down_slices: int = 8,
    ):
        self.enabled = enabled
        self.failure_probability = failure_probability
        self.rng = random.Random(random_seed)
        self.min_down_slices = min_down_slices
        self.max_down_slices = max_down_slices
        self.down_remaining: Dict[LinkKey, int] = {}
        self.blink_on: Dict[LinkKey, bool] = {}

    def step(self, candidate_keys: Iterable[LinkKey], active_keys: Set[LinkKey]) -> Set[LinkKey]:
        if not self.enabled:
            return set()

        down_keys: Set[LinkKey] = set()
        for key in candidate_keys:
            remaining = self.down_remaining.get(key, 0)
            if remaining > 0:
                blink_on = not self.blink_on.get(key, False)
                self.blink_on[key] = blink_on
                if blink_on:
                    down_keys.add(key)

                remaining -= 1
                if remaining > 0:
                    self.down_remaining[key] = remaining
                else:
                    self.down_remaining.pop(key, None)
                    self.blink_on.pop(key, None)
                continue

            if key in active_keys and self.rng.random() < self.failure_probability:
                duration = self.rng.randint(self.min_down_slices, self.max_down_slices)
                down_keys.add(key)
                if duration > 1:
                    self.down_remaining[key] = duration - 1
                    self.blink_on[key] = True

        return down_keys


class LinkDatasetExporter:
    """Generate SatSimPro-compatible satellite_*.txt files from the orbit model."""

    def export(
        self,
        *,
        orbit_num: int,
        sat_per_orbit: int,
        time_slices: int,
        duration_sec: float,
        output_dir: str,
        phase_factor: int = 0,
        altitude_km: float = 550.0,
        inclination_deg: float = 53.0,
        random_failure_enabled: bool = False,
        failure_probability: float = 0.0,
        random_seed: int = 42,
        strategy: Optional[Any] = None,
        start_time: Optional[datetime] = None,
        epoch_time: Optional[datetime] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> LinkDatasetExportResult:
        self._validate(
            orbit_num=orbit_num,
            sat_per_orbit=sat_per_orbit,
            time_slices=time_slices,
            duration_sec=duration_sec,
            failure_probability=failure_probability,
            output_dir=output_dir,
        )

        current_time = start_time or datetime.utcnow()
        walker_epoch_time = epoch_time or current_time
        strategy = strategy or GridDeltaStrategy()
        calculator = OrbitCalculator()
        calculator.generate_walker(
            orbit_num * sat_per_orbit,
            orbit_num,
            phase_factor,
            altitude_km,
            inclination_deg,
            walker_epoch_time,
        )

        calculator.propagate(current_time)
        strategy.compute_links(calculator.satellites)

        satellite_ids = self._satellite_ids(calculator.satellites)
        fixed_neighbors = self._build_fixed_neighbors(calculator.satellites, strategy)
        candidate_keys = {
            self._link_key(src, dst)
            for src, neighbors in fixed_neighbors.items()
            for dst in neighbors
        }
        histories: Dict[int, List[str]] = {idx: [] for idx in fixed_neighbors}

        failure_model = RandomLinkFailureModel(
            enabled=random_failure_enabled,
            failure_probability=failure_probability,
            random_seed=random_seed,
        )
        step_seconds = duration_sec / time_slices

        for time_index in range(time_slices):
            calculator.propagate(current_time)
            _isl, active_links = strategy.compute_links(calculator.satellites)
            active_latency = self._active_latency_map(active_links, calculator.satellites)
            down_by_random = failure_model.step(candidate_keys, set(active_latency))

            for sat_idx, neighbors in fixed_neighbors.items():
                row = [str(time_index)]
                for neighbor_idx in neighbors:
                    key = self._link_key(sat_idx, neighbor_idx)
                    if key in down_by_random or key not in active_latency:
                        row.append("down")
                    else:
                        row.append(f"{active_latency[key]:.8f}")
                histories[sat_idx].append(" ".join(row))

            current_time += timedelta(seconds=step_seconds)
            if progress_callback is not None and not progress_callback(time_index + 1, time_slices):
                raise LinkDatasetExportCancelled()

        output_dir = self._prepare_output_dir(output_dir)
        for sat_idx in sorted(fixed_neighbors, key=lambda idx: satellite_ids[idx]):
            path = os.path.join(output_dir, f"satellite_{satellite_ids[sat_idx]}.txt")
            with open(path, "w", encoding="utf-8") as file:
                file.write("Time\n")
                file.write(
                    " ".join(
                        f"Satellite_{satellite_ids[neighbor_idx]}"
                        for neighbor_idx in fixed_neighbors[sat_idx]
                    )
                    + "\n"
                )
                file.write(SEPARATOR + "\n")
                file.write("\n".join(histories[sat_idx]))
                file.write("\n")

        return LinkDatasetExportResult(
            output_dir=output_dir,
            file_count=len(fixed_neighbors),
            time_slices=time_slices,
        )

    def _validate(
        self,
        *,
        orbit_num: int,
        sat_per_orbit: int,
        time_slices: int,
        duration_sec: float,
        failure_probability: float,
        output_dir: str,
    ) -> None:
        if orbit_num < 3:
            raise ValueError("Orbit Num must be at least 3 to provide distinct plane neighbors.")
        if orbit_num > 99:
            raise ValueError("Orbit Num must be at most 99 for two-digit satellite IDs.")
        if sat_per_orbit < 3:
            raise ValueError(
                "Satellites Per Orbit must be at least 3 to provide distinct in-plane neighbors."
            )
        if sat_per_orbit > 99:
            raise ValueError("Satellites Per Orbit must be at most 99 for two-digit satellite IDs.")
        if time_slices < 1:
            raise ValueError("Time Slices must be at least 1.")
        if duration_sec <= 0:
            raise ValueError("Simulation Duration must be greater than 0.")
        if not 0.0 <= failure_probability <= 1.0:
            raise ValueError("Failure Probability must be between 0 and 1.")
        if not output_dir:
            raise ValueError("Output Directory is required.")

    def _prepare_output_dir(self, parent_dir: str) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_dir = os.path.join(parent_dir, f"LinkDataset_{timestamp}")
        output_dir = base_dir
        suffix = 1
        while os.path.exists(output_dir):
            suffix += 1
            output_dir = f"{base_dir}_{suffix}"

        os.makedirs(output_dir, exist_ok=False)
        return output_dir

    def _satellite_ids(self, satellites: List[Any]) -> Dict[int, str]:
        return {
            idx: f"1{sat.plane_idx + 1:02d}{sat.node_idx + 1:02d}"
            for idx, sat in enumerate(satellites)
        }

    def _build_fixed_neighbors(self, satellites: List[Any], strategy: Any) -> Dict[int, List[int]]:
        if not satellites or not getattr(satellites[0], "is_walker", False):
            return {}

        plane_count = max(sat.plane_idx for sat in satellites) + 1
        node_count = max(sat.node_idx for sat in satellites) + 1
        by_slot = {
            (sat.plane_idx, sat.node_idx): idx
            for idx, sat in enumerate(satellites)
            if sat.plane_idx >= 0 and sat.node_idx >= 0
        }

        static_edges = getattr(strategy, "static_edges", None)
        if static_edges:
            return self._build_delta_neighbors(satellites, by_slot, static_edges)

        neighbors: Dict[int, List[int]] = {}
        for idx, sat in enumerate(satellites):
            plane = sat.plane_idx
            node = sat.node_idx
            neighbors[idx] = [
                by_slot[((plane - 1) % plane_count, node)],
                by_slot[((plane + 1) % plane_count, node)],
                by_slot[(plane, (node - 1) % node_count)],
                by_slot[(plane, (node + 1) % node_count)],
            ]
        return neighbors

    def _build_delta_neighbors(
        self,
        satellites: List[Any],
        by_slot: Dict[Tuple[int, int], int],
        static_edges: List[Tuple[str, int, int]],
    ) -> Dict[int, List[int]]:
        plane_count = max(sat.plane_idx for sat in satellites) + 1
        node_count = max(sat.node_idx for sat in satellites) + 1

        inter_right: Dict[int, int] = {}
        inter_left: Dict[int, int] = {}
        intra_next: Dict[int, int] = {}
        intra_prev: Dict[int, int] = {}

        for edge_type, src, tgt in static_edges:
            if edge_type == "inter":
                inter_right[src] = tgt
                inter_left[tgt] = src
            elif edge_type == "intra":
                intra_next[src] = tgt
                intra_prev[tgt] = src

        neighbors: Dict[int, List[int]] = {}
        for idx, sat in enumerate(satellites):
            plane = sat.plane_idx
            node = sat.node_idx
            neighbors[idx] = [
                inter_left.get(idx, by_slot[((plane - 1) % plane_count, node)]),
                inter_right.get(idx, by_slot[((plane + 1) % plane_count, node)]),
                intra_prev.get(idx, by_slot[(plane, (node - 1) % node_count)]),
                intra_next.get(idx, by_slot[(plane, (node + 1) % node_count)]),
            ]
        return neighbors

    def _active_latency_map(
        self,
        active_links: List[Dict[str, Any]],
        satellites: List[Any],
    ) -> Dict[LinkKey, float]:
        active_latency: Dict[LinkKey, float] = {}
        for link in active_links:
            src = int(link["src"])
            tgt = int(link["tgt"])
            active_latency[self._link_key(src, tgt)] = self._latency_ms(
                satellites[src].position,
                satellites[tgt].position,
            )
        return active_latency

    def _latency_ms(self, src_position: np.ndarray, tgt_position: np.ndarray) -> float:
        distance_km = float(np.linalg.norm(src_position - tgt_position))
        return (distance_km / LIGHT_SPEED_KM_PER_S) * 1000.0

    def _link_key(self, src: int, tgt: int) -> LinkKey:
        return (src, tgt) if src < tgt else (tgt, src)
