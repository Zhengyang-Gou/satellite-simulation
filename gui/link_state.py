"""Small helpers and type aliases for link state shared by GUI modules."""

from typing import Any, Dict, Iterable, List, Tuple

import numpy as np

from .theme import DOWN

LinkKey = Tuple[int, int]
LinkRecord = Dict[str, Any]


def link_key(src: int, tgt: int) -> LinkKey:
    """Return a stable, direction-independent key for one ISL."""
    return (src, tgt) if src < tgt else (tgt, src)


def is_down(value: Any) -> bool:
    return str(value).lower() == DOWN


def satellite_positions_array(satellites: Iterable[Any]) -> np.ndarray:
    satellites = list(satellites)
    if not satellites:
        return np.empty((0, 3), dtype=np.float32)
    return np.array([s.position for s in satellites], dtype=np.float32)


def link_pairs_to_lines(link_pairs: Iterable[LinkKey]) -> np.ndarray:
    lines: List[int] = []
    for src, tgt in link_pairs:
        lines.extend([2, int(src), int(tgt)])
    return np.array(lines, dtype=np.int32) if lines else np.empty((0,), dtype=np.int32)
