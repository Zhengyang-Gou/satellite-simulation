import os
from PySide6.QtWidgets import QWidget, QVBoxLayout
from pyvistaqt import QtInteractor
import pyvista as pv
import numpy as np

class Visualizer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0,0,0,0)
        self.plotter = QtInteractor(self)
        self.layout.addWidget(self.plotter)
        
        self.cached_sat_pos = np.array([])
        self.cached_isl = np.array([])
        self.cached_path_lines = np.array([])
        
        self.sat_actor = None 
        self.isl_actor = None
        self.path_actor = None
        self._init_scene()

    def _init_scene(self):
        self.plotter.set_background('black')
        sphere = pv.Sphere(radius=6371, theta_resolution=120, phi_resolution=120)
        try: sphere = sphere.texture_map_to_sphere()
        except: pass
        if os.path.exists("assets/earth.jpg"):
            try:
                self.plotter.add_mesh(sphere, texture=pv.read_texture("assets/earth.jpg"), smooth_shading=True)
            except: pass
        else:
            self.plotter.add_mesh(sphere, color='#112233', style='wireframe', opacity=0.3)
        self.plotter.add_axes()
        self.plotter.camera.position = (20000, 0, 0)

    def update_scene(self, sat_positions, isl_lines, highlight_lines=None):
        self.cached_sat_pos = sat_positions
        self.cached_isl = isl_lines
        self.cached_path_lines = highlight_lines if highlight_lines is not None else np.array([])
        self._render_frame()

    def _render_frame(self):
        if len(self.cached_sat_pos) == 0: return
        sats = self.cached_sat_pos
        
        # 1. 卫星点云渲染
        if self.sat_actor:
            self.sat_actor.mapper.dataset.points = sats
        else:
            cloud = pv.PolyData(sats)
            self.sat_actor = self.plotter.add_mesh(cloud, color='white', point_size=8, render_points_as_spheres=True)

        # 2. 高亮链路渲染
        if len(self.cached_path_lines) > 0:
            if self.path_actor:
                self.path_actor.mapper.dataset.points = sats 
                self.path_actor.mapper.dataset.lines = self.cached_path_lines
                self.path_actor.SetVisibility(True)
            else:
                mesh_path = pv.PolyData(sats)
                mesh_path.lines = self.cached_path_lines
                self.path_actor = self.plotter.add_mesh(mesh_path, color='#FFD700', line_width=5, render_lines_as_tubes=True)
        elif self.path_actor: 
            self.path_actor.SetVisibility(False)

        # 3. 基础网格链路渲染
        if len(self.cached_isl) > 0:
            if self.isl_actor:
                self.isl_actor.mapper.dataset.points = sats
                self.isl_actor.mapper.dataset.lines = self.cached_isl
                self.isl_actor.SetVisibility(True)
            else:
                mesh = pv.PolyData(sats)
                mesh.lines = self.cached_isl
                self.isl_actor = self.plotter.add_mesh(mesh, color='#00AAFF', line_width=1, opacity=0.3)
        elif self.isl_actor: 
            self.isl_actor.SetVisibility(False)

        self.plotter.render()