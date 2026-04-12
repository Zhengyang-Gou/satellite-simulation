import os
import numpy as np
from datetime import datetime, timedelta

class DataExporter:
    def __init__(self):
        self.is_active = False; self.export_dir = None
        self.start_time_ref = None; self.end_time_ref = None; self.step_counter = 0

    def start(self, parent_dir, current_time, duration_sec):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.export_dir = os.path.join(parent_dir, f"Export_{timestamp}")
            if not os.path.exists(self.export_dir): os.makedirs(self.export_dir)
            self.is_active = True; self.step_counter = 0
            self.start_time_ref = current_time; self.end_time_ref = current_time + timedelta(seconds=duration_sec)
            return True, f"Saving to Export_{timestamp}"
        except Exception as e:
            self.stop(); return False, str(e)

    def _ecef_to_lla(self, x, y, z):
        a = 6378.137; b = 6356.752314245
        f = 1.0 / 298.257223563; e2 = 2*f - f*f; ep2 = (a**2 - b**2) / b**2 
        p = np.sqrt(x**2 + y**2); th = np.arctan2(a*z, b*p)
        lon_rad = np.arctan2(y, x); lat_rad = np.arctan2(z + ep2 * b * np.sin(th)**3, p - e2 * a * np.cos(th)**3)
        N = a / np.sqrt(1 - e2 * np.sin(lat_rad)**2)
        return np.degrees(lat_rad), np.degrees(lon_rad), p / np.cos(lat_rad) - N

    def record_frame(self, current_time, satellites, all_links_data):
        if not self.is_active or not self.export_dir: return
        try:
            fname = f"step_{self.step_counter:04d}_{current_time.strftime('%Y-%m-%d_%H-%M-%S')}.txt"
            with open(os.path.join(self.export_dir, fname), 'w') as f:
                f.write(f"[METADATA]\nTime: {current_time.strftime('%Y-%m-%d %H:%M:%S')}\nStep: {self.step_counter}\nTotal_Sats: {len(satellites)}\n\n")
                f.write("[NODES]\nID, Name, Lat(deg), Lon(deg), Alt(km)\n") 
                for i, s in enumerate(satellites):
                    if np.linalg.norm(s.position) > 100:
                        lat, lon, alt = self._ecef_to_lla(s.position[0], s.position[1], s.position[2])
                        f.write(f"{s.sat_id}, {s.name}, {lat:.5f}, {lon:.5f}, {alt:.3f}\n")
                
                # [核心修改] 导出内容增加 Latency 字段，并使用精确名字写入
                f.write("\n[LINKS]\nType, SourceName, TargetName, Latency(ms)\n") 
                for link in all_links_data:
                    f.write(f"ISL, {link['src_name']}, {link['tgt_name']}, {link['latency']:.4f}\n")
            self.step_counter += 1
        except Exception as e: print(f"Export error: {e}")

    def stop(self):
        self.is_active = False; self.export_dir = None