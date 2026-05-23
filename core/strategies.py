import numpy as np

class Strategy:
    def compute_links(self, satellites):
        raise NotImplementedError

    def _format_edges(self, edges, satellites):
        link_stats = []

        if not edges:
            return np.empty((0,), dtype=np.int64), link_stats

        edge_arr = np.asarray(sorted(edges), dtype=np.int64)
        u_list = edge_arr[:, 0]
        v_list = edge_arr[:, 1]

        isl_arr = np.empty(edge_arr.size + len(edge_arr), dtype=np.int64)
        isl_arr[0::3] = 2
        isl_arr[1::3] = u_list
        isl_arr[2::3] = v_list

        positions = np.asarray([s.position for s in satellites], dtype=np.float64)
        dists = np.linalg.norm(positions[u_list] - positions[v_list], axis=1)
        latencies = (dists / 299792.458) * 1000.0

        for i, (src, tgt) in enumerate(edge_arr):
            src = int(src)
            tgt = int(tgt)
            link_stats.append({
                'id': i + 1,
                'src': src,
                'tgt': tgt,
                'src_name': satellites[src].name,
                'tgt_name': satellites[tgt].name,
                'latency': round(float(latencies[i]), 4)
            })

        return isl_arr, link_stats

class GridStarStrategy(Strategy):
    def __init__(self, plane_tolerance=6.0, max_intra_dist=5000, max_inter_dist=5000):
        self.plane_tol = plane_tolerance; self.max_intra = max_intra_dist; self.max_inter = max_inter_dist
        
    def compute_links(self, satellites):
        if not satellites: return np.empty((0,), dtype=np.int64), []
        if getattr(satellites[0], 'is_walker', False):
            return self._compute_walker_links(satellites)

        return self._compute_grouped_links(satellites)

    def _compute_walker_links(self, satellites):
        try:
            plane_count = max(s.plane_idx for s in satellites) + 1
            node_count = max(s.node_idx for s in satellites) + 1
        except ValueError:
            return np.empty((0,), dtype=np.int64), []

        by_slot = {
            (sat.plane_idx, sat.node_idx): idx
            for idx, sat in enumerate(satellites)
            if sat.plane_idx >= 0 and sat.node_idx >= 0
        }

        isl_edges = set()
        def add_edge(u, v): isl_edges.add((u, v) if u < v else (v, u))

        for plane_idx in range(plane_count):
            next_plane = (plane_idx + 1) % plane_count
            for node_idx in range(node_count):
                current = by_slot.get((plane_idx, node_idx))
                if current is None:
                    continue

                same_plane_next = by_slot.get((plane_idx, (node_idx + 1) % node_count))
                if same_plane_next is not None:
                    dist = np.linalg.norm(satellites[current].position_eci - satellites[same_plane_next].position_eci)
                    if dist <= self.max_intra:
                        add_edge(current, same_plane_next)

                next_plane_same_node = by_slot.get((next_plane, node_idx))
                if next_plane_same_node is None:
                    continue

                dist = np.linalg.norm(satellites[current].position_eci - satellites[next_plane_same_node].position_eci)
                if dist <= self.max_inter:
                    add_edge(current, next_plane_same_node)

        return self._format_edges(isl_edges, satellites)

    def _compute_grouped_links(self, satellites):
        sats_data = []
        for i, s in enumerate(satellites):
            if not hasattr(s, 'position_eci') or np.linalg.norm(s.position_eci) < 100: continue
            rx, ry, rz = s.position_eci; raan_rad = np.radians(s.raan); inc_rad = np.radians(s.inclination)
            x_tmp = rx * np.cos(raan_rad) + ry * np.sin(raan_rad); y_tmp = -rx * np.sin(raan_rad) + ry * np.cos(raan_rad)
            y_plane = y_tmp * np.cos(inc_rad) + rz * np.sin(inc_rad); x_plane = x_tmp 
            u_angle = np.degrees(np.arctan2(y_plane, x_plane)) % 360.0
            curr_lat = np.degrees(np.arcsin(s.position[2] / np.linalg.norm(s.position)))
            sats_data.append({'idx': i, 'raan': s.raan, 'u': u_angle, 'pos_eci': s.position_eci, 'lat': curr_lat})

        if not sats_data: return np.empty((0,), dtype=np.int64), []
        sats_data.sort(key=lambda x: x['raan'])
        planes_list = []; current_plane = [sats_data[0]]
        for k in range(1, len(sats_data)):
            curr = sats_data[k]; prev = sats_data[k-1]
            # 优化：通过模运算计算最短角度差
            diff = abs((curr['raan'] - prev['raan'] + 180.0) % 360.0 - 180.0)
            if diff > self.plane_tol: planes_list.append(current_plane); current_plane = []
            current_plane.append(curr)
        planes_list.append(current_plane)

        isl_edges = set()
        def add_edge(u, v): isl_edges.add((u, v) if u < v else (v, u))
            
        num_planes = len(planes_list)
        for p_idx in range(num_planes):
            plane_nodes = planes_list[p_idx]; plane_nodes.sort(key=lambda x: x['u']); n_nodes = len(plane_nodes)
            if n_nodes > 1:
                for k in range(n_nodes):
                    u_node = plane_nodes[k]; v_node = plane_nodes[(k + 1) % n_nodes]
                    if np.linalg.norm(u_node['pos_eci'] - v_node['pos_eci']) <= self.max_intra: add_edge(u_node['idx'], v_node['idx'])
            
            if num_planes > 1:
                neighbor_plane = planes_list[(p_idx + 1) % num_planes]
                node_count = min(len(plane_nodes), len(neighbor_plane))
                u_pos = np.asarray([node['pos_eci'] for node in plane_nodes[:node_count]])
                neighbor_pos = np.asarray([node['pos_eci'] for node in neighbor_plane])
                shift_costs = []
                for shift in range(len(neighbor_plane)):
                    shifted_v_pos = np.roll(neighbor_pos, -shift, axis=0)[:node_count]
                    dists = np.linalg.norm(u_pos - shifted_v_pos, axis=1)
                    shift_costs.append(float(np.sum(dists)))
                best_shift = int(np.argmin(shift_costs))
                best_indices = (np.arange(node_count) + best_shift) % len(neighbor_plane)

                v_pos = np.asarray([neighbor_plane[idx]['pos_eci'] for idx in best_indices])
                inter_dists = np.linalg.norm(u_pos - v_pos, axis=1)

                allowed = inter_dists <= self.max_inter

                for node_idx, best_idx in enumerate(best_indices):
                    if allowed[node_idx]:
                        add_edge(plane_nodes[node_idx]['idx'], neighbor_plane[int(best_idx)]['idx'])

        return self._format_edges(isl_edges, satellites)

class GridDeltaStrategy(Strategy):
    def __init__(self):
        self.static_edges = None
        
    def compute_links(self, satellites):
        if not satellites or not getattr(satellites[0], 'is_walker', False): return np.empty((0,), dtype=np.int64), []
        if self.static_edges is None:
            self.static_edges = []; P = max(s.plane_idx for s in satellites) + 1; S = max(s.node_idx for s in satellites) + 1
            get_idx = lambda p, s: (p % P) * S + (s % S)
            for p in range(P):
                next_plane_positions = np.asarray([
                    satellites[get_idx(p + 1, ns)].position_eci
                    for ns in range(S)
                ])
                current_plane_positions = np.asarray([
                    satellites[get_idx(p, s)].position_eci
                    for s in range(S)
                ])
                shift_costs = []
                for shift in range(S):
                    shifted_positions = np.roll(next_plane_positions, -shift, axis=0)
                    dists = np.linalg.norm(current_plane_positions - shifted_positions, axis=1)
                    shift_costs.append(float(np.sum(dists)))
                best_shift = int(np.argmin(shift_costs))

                for s in range(S):
                    u_idx = get_idx(p, s); self.static_edges.append(('intra', u_idx, get_idx(p, s + 1)))
                    self.static_edges.append(('inter', u_idx, get_idx(p + 1, s + best_shift)))

        isl_edges = set()
        for edge_type, u, v in self.static_edges:
            isl_edges.add((u, v) if u < v else (v, u))
        return self._format_edges(isl_edges, satellites)
