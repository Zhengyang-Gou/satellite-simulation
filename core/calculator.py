from datetime import datetime

import numpy as np

from .models import Satellite


class OrbitCalculator:
    def __init__(self):
        self.satellites = []
        self.epoch_time = None

    def generate_walker(self, T, P, F, alt_km, inc_deg, current_time: datetime):
        self.satellites = []
        self.epoch_time = current_time
        S = T // P
        delta_raan = 360.0 / P
        delta_ma = 360.0 / S
        phase_shift = (F * 360.0) / T

        sat_id_counter = 0
        for p in range(P):
            for s in range(S):
                raan = p * delta_raan
                ma = (s * delta_ma + p * phase_shift) % 360.0
                name = f"{p+1:02d}{s+1:02d}"

                sat = Satellite(sat_id=sat_id_counter, name=name)
                sat.plane_idx = p
                sat.node_idx = s
                sat.altitude = alt_km
                sat.inclination = inc_deg
                sat.raan = raan
                sat.mean_anomaly = ma
                self.satellites.append(sat)
                sat_id_counter += 1
        return len(self.satellites)

    def propagate(self, current_time: datetime):
        jd = 2451545.0 + (current_time - datetime(2000, 1, 1, 12)).total_seconds() / 86400.0
        gst = self._gstime(jd)
        c, s = np.cos(gst), np.sin(gst)
        delta_t_sec = (current_time - self.epoch_time).total_seconds() if self.epoch_time is not None else 0.0
        R_earth = 6371.0
        mu = 3.986004418e5

        for sat in self.satellites:
            a = R_earth + sat.altitude
            n = np.sqrt(mu / (a**3))
            ma_current_rad = np.radians(sat.mean_anomaly) + n * delta_t_sec
            inc_rad = np.radians(sat.inclination)
            raan_rad = np.radians(sat.raan)

            x_plane = a * np.cos(ma_current_rad)
            y_plane = a * np.sin(ma_current_rad)
            x_eci = x_plane * np.cos(raan_rad) - y_plane * np.cos(inc_rad) * np.sin(raan_rad)
            y_eci = x_plane * np.sin(raan_rad) + y_plane * np.cos(inc_rad) * np.cos(raan_rad)
            z_eci = y_plane * np.sin(inc_rad)
            sat.position_eci = np.array([x_eci, y_eci, z_eci])

            x_ecef = x_eci * c + y_eci * s
            y_ecef = -x_eci * s + y_eci * c
            sat.position = np.array([x_ecef, y_ecef, z_eci])

    def _gstime(self, jdut1):
        tut1 = (jdut1 - 2451545.0) / 36525.0
        temp = -6.2e-6 * tut1**3 + 0.093104 * tut1**2 + (876600.0*3600 + 8640184.812866) * tut1 + 67310.54841
        temp = (temp * (np.pi/180.0) / 240.0) % (2*np.pi)
        if temp < 0:
            temp += 2*np.pi
        return temp
