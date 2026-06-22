from dataclasses import dataclass, field
import numpy as np


@dataclass
class Satellite:
    sat_id: int
    name: str

    position: np.ndarray = field(default_factory=lambda: np.array([0.0, 0.0, 0.0]))
    position_eci: np.ndarray = field(default_factory=lambda: np.array([0.0, 0.0, 0.0]))

    inclination: float = 0.0
    raan: float = 0.0
    mean_anomaly: float = 0.0
    altitude: float = 0.0

    plane_idx: int = -1
    node_idx: int = -1
