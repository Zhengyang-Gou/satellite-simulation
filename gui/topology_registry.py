"""Topology registry: stable full-link table plus per-frame link state updates."""

from typing import Any, Dict, List, Set

from core.strategies import GridDeltaStrategy

from .link_state import LinkKey, LinkRecord, is_down, link_key
from .theme import DOWN


class TopologyRegistry:
    REDIS_SMOOTHING = 0.22

    """
    Keeps a stable table of theoretically possible links.

    The simulation loop only updates each link's live state. It does not add/remove
    table rows every frame, so pagination and selection remain stable.
    """

    def __init__(self):
        self.link_registry: Dict[LinkKey, LinkRecord] = {}
        self.all_links_data: List[LinkRecord] = []
        self.active_link_keys: Set[LinkKey] = set()
        self.active_count = 0
        self.is_locked = False

    def reset(self, strategy: Any) -> None:
        self.link_registry.clear()
        self.all_links_data.clear()
        self.active_link_keys.clear()
        self.active_count = 0
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
        self.active_link_keys.clear()
        self.active_count = 0

        if not satellites:
            self.all_links_data = []
            return

        self._build_delta_registry(strategy, satellites)

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

    def _new_link_record(self, src: int, tgt: int, satellites: List[Any]) -> LinkRecord:
        return {
            "src": src,
            "tgt": tgt,
            "src_name": satellites[src].name,
            "tgt_name": satellites[tgt].name,
            "latency": DOWN,
            "redis_cal_pct": DOWN,
            "redis_loss_pct": DOWN,
            "_redis_cal_target": DOWN,
            "_redis_loss_target": DOWN,
        }

    def apply_active_links(self, active_links: List[LinkRecord]) -> None:
        current_active_keys = set()

        for active in active_links:
            key = link_key(active["src"], active["tgt"])
            record = self.link_registry.get(key)
            if record is None:
                continue

            record["latency"] = active["latency"]
            self._advance_redis_display(record)
            current_active_keys.add(key)

        for key in self.active_link_keys - current_active_keys:
            record = self.link_registry.get(key)
            if record is None:
                continue

            record["latency"] = DOWN
            record["redis_cal_pct"] = DOWN
            record["redis_loss_pct"] = DOWN
            record["_redis_cal_target"] = DOWN
            record["_redis_loss_target"] = DOWN

        self.active_link_keys = current_active_keys
        self.active_count = len(current_active_keys)

    def _advance_redis_display(self, record: LinkRecord) -> None:
        record["redis_cal_pct"] = self._smooth_metric(
            record.get("redis_cal_pct", DOWN),
            record.get("_redis_cal_target", DOWN),
        )
        record["redis_loss_pct"] = self._smooth_metric(
            record.get("redis_loss_pct", DOWN),
            record.get("_redis_loss_target", DOWN),
        )

    def active_for_redis(self) -> List[LinkRecord]:
        return [
            {"src": record["src"], "tgt": record["tgt"]}
            for key in self.active_link_keys
            if (record := self.link_registry.get(key)) is not None
            and not is_down(record.get("latency"))
        ]

    def apply_redis_cal(self, redis_cal_map: Dict[LinkKey, Any]) -> None:
        for key in self.active_link_keys:
            record = self.link_registry.get(key)
            if record is None:
                continue

            if is_down(record.get("latency", DOWN)):
                record["redis_cal_pct"] = DOWN
                record["redis_loss_pct"] = DOWN
                continue

            target = redis_cal_map.get((record["src"], record["tgt"]), DOWN)
            record["_redis_cal_target"] = target
            record["redis_cal_pct"] = self._smooth_metric(record.get("redis_cal_pct", DOWN), target)

    def apply_redis_loss(self, redis_loss_map: Dict[LinkKey, Any]) -> None:
        for key in self.active_link_keys:
            record = self.link_registry.get(key)
            if record is None:
                continue

            if is_down(record.get("latency", DOWN)):
                record["redis_loss_pct"] = DOWN
                continue

            target = redis_loss_map.get((record["src"], record["tgt"]), DOWN)
            record["_redis_loss_target"] = target
            record["redis_loss_pct"] = self._smooth_metric(record.get("redis_loss_pct", DOWN), target)

    def _smooth_metric(self, current: Any, target: Any) -> Any:
        if is_down(target):
            return DOWN
        if is_down(current):
            return target

        try:
            current_f = float(current)
            target_f = float(target)
        except (TypeError, ValueError):
            return target

        value = current_f + (target_f - current_f) * self.REDIS_SMOOTHING
        return round(value, 4)

    def mark_redis_down(self) -> None:
        for record in self.link_registry.values():
            record["redis_cal_pct"] = DOWN
            record["redis_loss_pct"] = DOWN
            record["_redis_cal_target"] = DOWN
            record["_redis_loss_target"] = DOWN
