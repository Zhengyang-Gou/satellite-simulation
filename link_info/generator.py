"""Generate OVS port mappings for fixed satellite links."""


def generate_link_info(satellites, fixed_neighbors, satellite_ids) -> str:
    """Return the contents of a link_info file for the supplied constellation."""
    lines = []
    emitted = set()
    for satellite_idx, neighbors in fixed_neighbors.items():
        satellite = satellites[satellite_idx]
        sat_id = satellite_ids[satellite_idx]
        for neighbor_idx in neighbors:
            neighbor = satellites[neighbor_idx]
            neighbor_id = satellite_ids[neighbor_idx]
            _append_link(lines, emitted, satellite, neighbor, sat_id, neighbor_id)
            _append_link(lines, emitted, neighbor, satellite, neighbor_id, sat_id)

    return "\n".join(lines)


def _append_link(lines, emitted, satellite, neighbor, sat_id, neighbor_id):
    key = (sat_id, neighbor_id)
    if key in emitted:
        return

    emitted.add(key)
    self_port, neighbor_port = _ports_for_link(satellite, neighbor)
    lines.append(
        f"{sat_id}-{neighbor_id} "
        f"S{sat_id}_{self_port}-S{neighbor_id}_{neighbor_port} "
        f"brA{sat_id}_{self_port}-brA{neighbor_id}_{neighbor_port}"
    )


def _ports_for_link(satellite, neighbor):
    if satellite.plane_idx == neighbor.plane_idx:
        if satellite.node_idx < neighbor.node_idx:
            return 2, 1
        return 1, 2

    if satellite.plane_idx < neighbor.plane_idx:
        return 3, 4
    return 4, 3
