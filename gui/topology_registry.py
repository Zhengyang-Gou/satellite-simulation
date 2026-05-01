"""Topology registry: stable full-link table plus per-frame link state updates."""

from typing import Any, Dict, List

from core.strategies import GridDeltaStrategy

from .link_state import LinkKey, LinkRecord, is_down, link_key
from .theme import DOWN


class TopologyRegistry:
    """
    Keeps a stable table of theoretically possible links.

    The simulation loop only updates each link's live state. It does not add/remove
    table rows every frame, so pagination and selection remain stable.
    """

    def __init__(self):
        self.link_registry: Dict[LinkKey, LinkRecord] = {}
        self.all_links_data: List[LinkRecord] = []
        self.is_locked = False

    def reset(self, strategy: Any) -> None:
        self.link_registry.clear()
        self.all_links_data.clear()
        self.is_locked = False

        if isinstance(strategy, GridDeltaStrategy):
            strategy.static_edges = None

    def build_if_needed(self, strategy: Any, satellites: List[Any]) -> None:
        if self.is_locked:
            return
        self.build(strategy, satellites)
        self.is_locked = True

    def build(self, strategy: Any, satellites: List[Any]) -> None:
        """Build the complete theoretical topology for the current strategy."""
        self.link_registry.clear()

        if not satellites:
            self.all_links_data = []
            return

        if isinstance(strategy, GridDeltaStrategy):
            self._build_delta_registry(strategy, satellites)
        else:
            self._build_star_registry(strategy, satellites)

        self.all_links_data = sorted(self.link_registry.values(), key=lambda x: (x["src_name"], x["tgt_name"]))
        for idx, record in enumerate(self.all_links_data, start=1):
            record["id"] = idx

    def _build_delta_registry(self, strategy: GridDeltaStrategy, satellites: List[Any]) -> None:
        if strategy.static_edges is None:
            strategy.compute_links(satellites)

        if not strategy.static_edges:
            return

        for _edge_type, src, tgt in strategy.static_edges:
            self.link_registry[link_key(src, tgt)] = self._new_link_record(src, tgt, satellites)

    def _build_star_registry(self, strategy: Any, satellites: List[Any]) -> None:
        all_links = self._compute_all_possible_star_links(strategy, satellites)
        for record in all_links:
            self.link_registry[link_key(record["src"], record["tgt"])] = self._new_link_record(
                record["src"],
                record["tgt"],
                satellites,
            )

    def _compute_all_possible_star_links(self, strategy: Any, satellites: List[Any]) -> List[LinkRecord]:
        old_intra = strategy.max_intra
        old_inter = strategy.max_inter
        old_polar = strategy.enable_polar_cut

        try:
            strategy.max_intra = 999999
            strategy.max_inter = 999999
            strategy.enable_polar_cut = False
            _isl, all_links = strategy.compute_links(satellites)
            return all_links
        finally:
            strategy.max_intra = old_intra
            strategy.max_inter = old_inter
            strategy.enable_polar_cut = old_polar

    def _new_link_record(self, src: int, tgt: int, satellites: List[Any]) -> LinkRecord:
        return {
            "src": src,
            "tgt": tgt,
            "src_name": satellites[src].name,
            "tgt_name": satellites[tgt].name,
            "latency": DOWN,
            "redis_delay_ms": DOWN,
            "redis_ratio_pct": DOWN,
        }

    def apply_active_links(self, active_links: List[LinkRecord]) -> None:
        current_active_keys = set()

        for active in active_links:
            key = link_key(active["src"], active["tgt"])
            record = self.link_registry.get(key)
            if record is None:
                continue

            record["latency"] = active["latency"]
            current_active_keys.add(key)

        for key, record in self.link_registry.items():
            if key not in current_active_keys:
                record["latency"] = DOWN
                record["redis_delay_ms"] = DOWN
                record["redis_ratio_pct"] = DOWN

    def active_for_redis(self) -> List[LinkRecord]:
        return [
            {"src": d["src"], "tgt": d["tgt"], "latency": d.get("latency", DOWN)}
            for d in self.link_registry.values()
            if not is_down(d.get("latency"))
        ]

    def apply_redis_delays(self, redis_delay_map: Dict[LinkKey, Any]) -> None:
        for record in self.link_registry.values():
            calc_latency = record.get("latency", DOWN)
            if is_down(calc_latency):
                record["redis_delay_ms"] = DOWN
                record["redis_ratio_pct"] = DOWN
                continue

            redis_delay = redis_delay_map.get((record["src"], record["tgt"]), DOWN)
            record["redis_delay_ms"] = redis_delay

            if is_down(redis_delay):
                record["redis_ratio_pct"] = DOWN
                continue

            try:
                calc_latency_f = float(calc_latency)
                redis_delay_f = float(redis_delay)
                record["redis_ratio_pct"] = (
                    round((redis_delay_f / calc_latency_f) * 100.0, 2)
                    if calc_latency_f > 0
                    else DOWN
                )
            except (TypeError, ValueError, ZeroDivisionError):
                record["redis_ratio_pct"] = DOWN

    def mark_redis_down(self) -> None:
        for record in self.link_registry.values():
            record["redis_delay_ms"] = DOWN
            record["redis_ratio_pct"] = DOWN
