from sgp4.api import Satrec, jday
import numpy as np
from datetime import datetime
from .models import Satellite

class OrbitCalculator:
    def __init__(self):
        self.satellites = []
        self.epoch_time = None # [新增] 记录 Walker 星座生成的基准时间

    def load_tle_data(self, tle_text, filter_alt=None, alt_tol=50, filter_inc=None, inc_tol=1.0):
        lines = tle_text.strip().split('\n')
        self.satellites = []
        self.epoch_time = None # 清除基准时间
        lines = [L.strip() for L in lines if L.strip()]
        
        mu = 3.986004418e14
        R_earth = 6371.0
        
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.startswith("1 "):
                l1 = lines[i]; l2 = lines[i+1]; i += 2; name = f"SAT"
            else:
                name = line; l1 = lines[i+1]; l2 = lines[i+2]; i += 3

            try:
                satrec = Satrec.twoline2rv(l1, l2)
                n = satrec.no_kozai / 60.0
                if n > 0:
                    a = (mu / (n ** 2)) ** (1.0 / 3)
                    alt_km = (a / 1000.0) - R_earth
                else:
                    alt_km = 0
                inclination_deg = np.degrees(satrec.inclo) % 360.0

                keep = True
                if filter_alt is not None and abs(alt_km - filter_alt) > alt_tol: keep = False
                if filter_inc is not None and keep and abs(inclination_deg - filter_inc) > inc_tol: keep = False

                if keep:
                    if name == "SAT": name = f"SAT-{satrec.satnum}"
                    sat = Satellite(sat_id=satrec.satnum, name=name, line1=l1, line2=l2)
                    sat._sgp4 = satrec
                    sat.altitude = float(alt_km)
                    sat.inclination = float(inclination_deg)
                    sat.raan = float(np.degrees(satrec.nodeo) % 360.0)
                    sat.is_walker = False
                    
                    sat.position = np.array([0.0, 0.0, 0.0])     
                    sat.position_eci = np.array([0.0, 0.0, 0.0]) 
                    self.satellites.append(sat)
            except:
                pass     
        return len(self.satellites)

    def generate_walker(self, T, P, F, alt_km, inc_deg, current_time: datetime):
        """
        生成纯数学定义的 Walker Delta 星座
        """
        self.satellites = []
        self.epoch_time = current_time # 记录推演的 0 时刻
        
        S = T // P  # 每个轨道面的卫星数
        delta_raan = 360.0 / P
        delta_ma = 360.0 / S
        phase_shift = (F * 360.0) / T  # 相位偏置
        
        sat_id_counter = 0
        for p in range(P):
            for s in range(S):
                # 1. 计算初始开普勒参数
                raan = p * delta_raan
                ma = (s * delta_ma + p * phase_shift) % 360.0
                
                # 2. 实例化卫星
                name = f"W-{p:02d}-{s:02d}"
                sat = Satellite(sat_id=sat_id_counter, name=name, line1="", line2="")
                
                sat.is_walker = True
                sat.plane_idx = p
                sat.node_idx = s
                
                sat.altitude = alt_km
                sat.inclination = inc_deg
                sat.raan = raan
                sat.mean_anomaly = ma
                sat.arg_perigee = 0.0 
                
                sat._sgp4 = None # 纯数学卫星不需要 SGP4 实例
                
                self.satellites.append(sat)
                sat_id_counter += 1
                
        return len(self.satellites)

    def propagate(self, current_time: datetime):
        jd, fr = jday(current_time.year, current_time.month, current_time.day,
                      current_time.hour, current_time.minute, current_time.second)
        gst = self._gstime(jd + fr)
        c, s = np.cos(gst), np.sin(gst)

        # 计算时间差 (秒)，用于推演 Walker 卫星的轨道相位
        delta_t_sec = 0.0
        if self.epoch_time is not None:
            delta_t_sec = (current_time - self.epoch_time).total_seconds()

        R_earth = 6371.0
        mu = 3.986004418e5 # 地球引力常数 (km^3/s^2)

        for sat in self.satellites:
            if sat.is_walker:
                # === 高速解析几何推演 ===
                a = R_earth + sat.altitude
                n = np.sqrt(mu / (a**3)) # 平均角速度 (rad/s)
                
                # 计算当前时刻的平近点角 (弧度)
                ma_current_rad = np.radians(sat.mean_anomaly) + n * delta_t_sec
                inc_rad = np.radians(sat.inclination)
                raan_rad = np.radians(sat.raan)
                
                # 1. 轨道面内坐标
                x_plane = a * np.cos(ma_current_rad)
                y_plane = a * np.sin(ma_current_rad)
                
                # 2. 旋转到 ECI (地心惯性坐标系)
                x_eci = x_plane * np.cos(raan_rad) - y_plane * np.cos(inc_rad) * np.sin(raan_rad)
                y_eci = x_plane * np.sin(raan_rad) + y_plane * np.cos(inc_rad) * np.cos(raan_rad)
                z_eci = y_plane * np.sin(inc_rad)
                
                sat.position_eci = np.array([x_eci, y_eci, z_eci])
                
                # 3. 旋转到 ECEF (随地球自转的坐标系)
                x_ecef = x_eci * c + y_eci * s
                y_ecef = -x_eci * s + y_eci * c
                z_ecef = z_eci
                
                sat.position = np.array([x_ecef, y_ecef, z_ecef])
            else:
                # === 原有的 SGP4 推演逻辑 ===
                if sat._sgp4 is None: continue
                e, r, v = sat._sgp4.sgp4(jd, fr)
                if e == 0:
                    sat.position_eci = np.array(r)
                    x, y, z = r
                    x_ecef = x * c + y * s
                    y_ecef = -x * s + y * c
                    z_ecef = z
                    sat.position = np.array([x_ecef, y_ecef, z_ecef])
                else:
                    sat.position = np.array([0.0, 0.0, 0.0])
                    sat.position_eci = np.array([0.0, 0.0, 0.0])

    def _gstime(self, jdut1):
        tut1 = (jdut1 - 2451545.0) / 36525.0
        temp = -6.2e-6 * tut1**3 + 0.093104 * tut1**2 + \
               (876600.0*3600 + 8640184.812866) * tut1 + 67310.54841
        temp = (temp * (np.pi/180.0) / 240.0) % (2*np.pi)
        if temp < 0: temp += 2*np.pi
        return temp