import os

import numpy as np
import pyvista as pv
from pyvistaqt import QtInteractor
from PySide6.QtWidgets import QVBoxLayout, QWidget


class Visualizer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.plotter = QtInteractor(self)
        self.layout.addWidget(self.plotter)

        self.cached_sat_pos = np.empty((0, 3), dtype=np.float64)
        self.cached_isl = np.empty((0,), dtype=np.int64)
        self.cached_path_lines = np.empty((0,), dtype=np.int64)

        self.sat_actor = None
        self.isl_actor = None
        self.path_actor = None

        self._init_scene()

    def _init_scene(self) -> None:
        self.plotter.set_background("#1e1e1e")

        sphere = pv.Sphere(
            radius=6371,
            theta_resolution=120,
            phi_resolution=120,
        )

        try:
            sphere = sphere.texture_map_to_sphere()
        except Exception:
            pass

        if os.path.exists("assets/earth.jpg"):
            try:
                texture = pv.read_texture("assets/earth.jpg")
                self.plotter.add_mesh(
                    sphere,
                    texture=texture,
                    smooth_shading=True,
                )
            except Exception:
                self.plotter.add_mesh(
                    sphere,
                    color="#112233",
                    style="wireframe",
                    opacity=0.3,
                )
        else:
            self.plotter.add_mesh(
                sphere,
                color="#112233",
                style="wireframe",
                opacity=0.3,
            )

        self.plotter.add_axes()

        self.plotter.camera_position = [
            (35000, 25000, 15000),
            (0, 0, 0),
            (0, 0, 1),
        ]

        try:
            self.plotter.enable_anti_aliasing("msaa", multi_samples=4)
        except Exception:
            pass

        try:
            self.plotter.enable_depth_peeling()
        except Exception:
            pass

    def update_scene(self, sat_positions, isl_lines, highlight_lines=None) -> None:
        self.cached_sat_pos = self._normalize_points(sat_positions)
        self.cached_isl = self._normalize_lines(isl_lines)

        if highlight_lines is None:
            self.cached_path_lines = np.empty((0,), dtype=np.int64)
        else:
            self.cached_path_lines = self._normalize_lines(highlight_lines)

        self._render_frame()

    def _normalize_points(self, sat_positions) -> np.ndarray:
        if sat_positions is None:
            return np.empty((0, 3), dtype=np.float64)

        points = np.asarray(sat_positions, dtype=np.float64)

        if points.size == 0:
            return np.empty((0, 3), dtype=np.float64)

        points = points.reshape((-1, 3))
        return np.ascontiguousarray(points, dtype=np.float64)

    def _normalize_lines(self, lines) -> np.ndarray:
        if lines is None:
            return np.empty((0,), dtype=np.int64)

        arr = np.asarray(lines, dtype=np.int64).reshape(-1)

        if arr.size == 0:
            return np.empty((0,), dtype=np.int64)

        if arr.size % 3 != 0:
            return np.empty((0,), dtype=np.int64)

        if not np.all(arr[0::3] == 2):
            return np.empty((0,), dtype=np.int64)

        return np.ascontiguousarray(arr, dtype=np.int64)

    def _remove_actor(self, actor_name: str) -> None:
        actor = getattr(self, actor_name)

        if actor is None:
            return

        try:
            self.plotter.remove_actor(actor)
        except Exception:
            pass

        setattr(self, actor_name, None)

    def _render_frame(self) -> None:
        if len(self.cached_sat_pos) == 0:
            return

        sats = self.cached_sat_pos

        self._render_satellites(sats)
        self._render_isl_links(sats)
        self._render_highlight_links(sats)

        self.plotter.render()

    def _render_satellites(self, sats: np.ndarray) -> None:
        if self.sat_actor:
            try:
                dataset = self.sat_actor.mapper.dataset
                dataset.points = sats
                dataset.Modified()
                self.sat_actor.mapper.Modified()
                return
            except Exception:
                self._remove_actor("sat_actor")

        cloud = pv.PolyData(sats)

        self.sat_actor = self.plotter.add_mesh(
            cloud,
            color="white",
            point_size=8,
            render_points_as_spheres=True,
        )

    def _render_isl_links(self, sats: np.ndarray) -> None:
        """
        Render normal ISL links.

        Important:
        Do not update dataset.lines in-place here. In some PyVista/VTK versions,
        changing the line cell array in-place does not reliably refresh the actor.
        Rebuilding the line actor is more stable.
        """
        if len(self.cached_isl) == 0:
            self._remove_actor("isl_actor")
            return

        self._remove_actor("isl_actor")

        mesh = pv.PolyData(sats)
        mesh.lines = self.cached_isl

        self.isl_actor = self.plotter.add_mesh(
            mesh,
            color="#00AAFF",
            line_width=2,
            opacity=0.85,
            render_lines_as_tubes=True,
        )

    def _render_highlight_links(self, sats: np.ndarray) -> None:
        """
        Render selected/highlighted links.

        This is also rebuilt each frame for the same reason as normal ISL links.
        """
        if len(self.cached_path_lines) == 0:
            self._remove_actor("path_actor")
            return

        self._remove_actor("path_actor")

        mesh_path = pv.PolyData(sats)
        mesh_path.lines = self.cached_path_lines

        self.path_actor = self.plotter.add_mesh(
            mesh_path,
            color="#FFD700",
            line_width=6,
            render_lines_as_tubes=True,
        )