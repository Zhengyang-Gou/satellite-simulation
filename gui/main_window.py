"""Main application window after modularizing UI, table, topology, and Redis concerns."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

from PySide6.QtCore import Qt, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QInputDialog,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from core.calculator import OrbitCalculator
from core.exporter import DataExporter
from core.strategies import GridDeltaStrategy, GridStarStrategy

from .config import env_int, redis_config_from_env
from .dialogs import ExportDialog, RedisSettingsDialog, TopologyDialog, WalkerDialog
from .link_state import LinkKey, link_pairs_to_lines, satellite_positions_array
from .redis_worker import RedisQueryWorker
from .table_panel import LinkTablePanel
from .theme import DARK_THEME
from .topology_registry import TopologyRegistry
from .visualizer import Visualizer


class MainWindow(QMainWindow):
    redis_query_requested = Signal(int, object, object)

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Satellite Network Simulation Pro")
        self.resize(1200, 900)
        self.setStyleSheet(DARK_THEME)

        self.calculator = OrbitCalculator()
        self.exporter = DataExporter()
        self.strategy = GridStarStrategy()
        self.strategy_idx = 0
        self.registry = TopologyRegistry()

        self.redis_config = redis_config_from_env()
        self.redis_enabled = bool(self.redis_config.get("enabled", False))
        self.redis_query_interval = env_int("SATNET_REDIS_QUERY_INTERVAL", 2)
        self.redis_query_counter = 0
        self.redis_query_seq = 0
        self.redis_query_in_flight = False
        self.redis_last_error = ""
        self.redis_worker_thread: Optional[QThread] = None
        self.redis_worker: Optional[RedisQueryWorker] = None

        if self.redis_enabled:
            self.start_redis_worker(self.redis_config)

        self.step_size = 1.0
        self.is_playing = False
        self.current_time = datetime.utcnow()
        self.selected_link_pairs: Set[LinkKey] = set()

        self._init_ui()
        self._init_menu()
        self.statusBar().showMessage("Ready")

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.loop)

    def start_redis_worker(self, redis_config: Dict[str, Any]) -> None:
        self.stop_redis_worker()

        self.redis_worker_thread = QThread(self)
        self.redis_worker = RedisQueryWorker(redis_config)
        self.redis_worker.moveToThread(self.redis_worker_thread)
        self.redis_query_requested.connect(self.redis_worker.query)
        self.redis_worker.result_ready.connect(self._apply_redis_result)
        self.redis_worker.error.connect(self._handle_redis_error)
        self.redis_worker_thread.start()

    def stop_redis_worker(self) -> None:
        self.redis_query_seq += 1
        self.redis_query_in_flight = False

        if self.redis_worker is not None:
            try:
                self.redis_query_requested.disconnect(self.redis_worker.query)
            except (TypeError, RuntimeError):
                pass

            try:
                self.redis_worker.close()
            except Exception:
                pass

        if self.redis_worker_thread is not None:
            self.redis_worker_thread.quit()
            self.redis_worker_thread.wait(1500)

        self.redis_worker = None
        self.redis_worker_thread = None

    def _init_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Vertical)

        self.visualizer = Visualizer()
        splitter.addWidget(self.visualizer)

        self.table_panel = LinkTablePanel(page_size=10)
        self.table_panel.selection_changed.connect(self._on_selected_links_changed)
        splitter.addWidget(self.table_panel)

        splitter.setStretchFactor(0, 6)
        splitter.setStretchFactor(1, 4)
        layout.addWidget(splitter)

    def _init_menu(self) -> None:
        mb = self.menuBar()

        m_data = mb.addMenu("Data")
        m_data.addAction("Load TLE File...", self.load_tle_file)
        m_data.addAction("Generate Walker...", self.open_walker_gen)

        m_topo = mb.addMenu("Topology")
        m_topo.addAction("Settings...", self.open_topology_settings)

        m_sim = mb.addMenu("Simulation")

        self.act_play = QAction("Start", self)
        self.act_play.triggered.connect(self.toggle_sim)
        self.act_play.setEnabled(False)

        m_sim.addAction(self.act_play)
        m_sim.addAction("Set Step Size...", self.open_step_settings)
        m_sim.addSeparator()
        m_sim.addAction("Export Simulation Data...", self.open_export_settings)

        m_redis = mb.addMenu("Redis")

        self.act_redis_enable = QAction("Enable Redis Query", self)
        self.act_redis_enable.setCheckable(True)
        self.act_redis_enable.setChecked(self.redis_enabled)
        self.act_redis_enable.toggled.connect(self.toggle_redis_query)

        m_redis.addAction(self.act_redis_enable)
        m_redis.addAction("Connection Settings...", self.open_redis_settings)

    def _set_redis_action_checked(self, checked: bool) -> None:
        if not hasattr(self, "act_redis_enable"):
            return
        self.act_redis_enable.blockSignals(True)
        self.act_redis_enable.setChecked(checked)
        self.act_redis_enable.blockSignals(False)

    def toggle_redis_query(self, enabled: bool) -> None:
        if enabled:
            self.redis_config["enabled"] = True
            self.redis_enabled = True
            self.redis_last_error = ""
            self.start_redis_worker(self.redis_config)
        else:
            self.redis_enabled = False
            self.redis_config["enabled"] = False
            self.stop_redis_worker()
            self.redis_last_error = ""
            self.registry.mark_redis_down()

        self.redis_query_counter = 0
        self._set_redis_action_checked(self.redis_enabled)
        self._refresh_table()

    def open_redis_settings(self) -> None:
        dlg = RedisSettingsDialog(self.redis_config, self)
        if dlg.exec() != QDialog.Accepted:
            return

        new_config = dlg.config()
        need_restart = self.redis_enabled or bool(new_config.get("enabled", False))

        if need_restart:
            self.stop_redis_worker()

        self.redis_config = new_config
        self.redis_enabled = bool(new_config.get("enabled", False))
        self.redis_query_counter = 0
        self.redis_query_in_flight = False
        self.redis_last_error = ""
        self.registry.mark_redis_down()

        if self.redis_enabled:
            self.start_redis_worker(self.redis_config)

        self._set_redis_action_checked(self.redis_enabled)
        self._refresh_table()

    def _on_selected_links_changed(self, selected: Set[LinkKey]) -> None:
        self.selected_link_pairs = selected

        if not self.is_playing:
            self.visualizer.update_scene(
                satellite_positions_array(self.calculator.satellites),
                self.visualizer.cached_isl,
                highlight_lines=link_pairs_to_lines(self.selected_link_pairs),
            )

    def reset_simulation_state(self) -> None:
        self.registry.reset(self.strategy)
        self.table_panel.reset()
        self.selected_link_pairs.clear()
        self.redis_query_counter = 0
        self.redis_query_seq += 1
        self.redis_query_in_flight = False
        self.redis_last_error = ""

    def _refresh_table(self) -> None:
        self.table_panel.selected_link_pairs = set(self.selected_link_pairs)
        self.table_panel.set_records(
            self.registry.all_links_data,
            redis_in_flight=self.redis_query_in_flight,
            redis_last_error=self.redis_last_error,
            active_count=self.registry.active_count,
        )

    def open_walker_gen(self) -> None:
        dlg = WalkerDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return

        total = dlg.spin_t.value()
        planes = dlg.spin_p.value()

        if total % planes != 0:
            QMessageBox.warning(
                self,
                "Walker Error",
                "Total Satellites (T) must be divisible by Orbital Planes (P).",
            )
            return

        count = self.calculator.generate_walker(
            total,
            planes,
            dlg.spin_f.value(),
            dlg.spin_alt.value(),
            dlg.spin_inc.value(),
            self.current_time,
        )

        if count:
            self.reset_simulation_state()
            self.act_play.setEnabled(True)
            self.loop(advance=False)

    def open_topology_settings(self) -> None:
        dlg = TopologyDialog(self.strategy_idx, self)
        if dlg.exec() != QDialog.Accepted:
            return

        self.strategy_idx = dlg.combo_strat.currentIndex()

        if self.strategy_idx == 0:
            self.strategy = GridStarStrategy(
                plane_tolerance=dlg.spin_plane_tol.value(),
                max_intra_dist=dlg.spin_intra.value(),
                max_inter_dist=dlg.spin_inter.value(),
            )
        else:
            self.strategy = GridDeltaStrategy()

        self.reset_simulation_state()
        if self.calculator.satellites:
            self.loop(advance=False)

    def open_step_settings(self) -> None:
        value, ok = QInputDialog.getDouble(
            self,
            "Set Step Size",
            "Enter simulation step size in seconds:",
            self.step_size,
            0.1,
            3600.0,
            1,
        )
        if ok:
            self.step_size = value

    def open_export_settings(self) -> None:
        dlg = ExportDialog(self)
        if dlg.exec() != QDialog.Accepted or not dlg.path:
            return

        ok, message = self.exporter.start(dlg.path, self.current_time, dlg.spin_duration.value())
        if ok:
            QMessageBox.information(self, "Export", "Export started.")
        else:
            QMessageBox.warning(self, "Export", message)

    def load_tle_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Open TLE", "", "Files (*.txt *.tle)")
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                count = self.calculator.load_tle_data(file.read())
        except UnicodeDecodeError:
            with open(file_path, "r", encoding="latin-1") as file:
                count = self.calculator.load_tle_data(file.read())
        except OSError as exc:
            QMessageBox.warning(self, "Load TLE", f"Failed to open file:\n{exc}")
            return

        if count:
            self.reset_simulation_state()
            self.act_play.setEnabled(True)
            self.loop(advance=False)
        else:
            QMessageBox.warning(self, "Load TLE", "No valid satellites were loaded from this TLE file.")

    def toggle_sim(self) -> None:
        self.is_playing = not self.is_playing
        self.act_play.setText("Pause" if self.is_playing else "Start")

        if self.is_playing:
            self.timer.start(100)
        else:
            self.timer.stop()

    def _schedule_redis_update_if_needed(self) -> None:
        if not self.redis_enabled or self.redis_worker is None:
            return

        self.redis_query_counter += 1
        if self.redis_query_counter % self.redis_query_interval != 0:
            return
        if self.redis_query_in_flight:
            return

        active_for_redis = self.registry.active_for_redis()
        if not active_for_redis or not self.calculator.satellites:
            return

        self.redis_query_seq += 1
        self.redis_query_in_flight = True
        self.redis_last_error = ""
        self.redis_query_requested.emit(
            self.redis_query_seq,
            active_for_redis,
            list(self.calculator.satellites),
        )

    @Slot(int, object)
    def _apply_redis_result(self, query_id: int, redis_result: Dict[str, Dict[LinkKey, Any]]) -> None:
        if query_id != self.redis_query_seq:
            return

        self.redis_query_in_flight = False
        self.redis_last_error = ""
        if isinstance(redis_result, dict) and "cal" in redis_result:
            self.registry.apply_redis_cal(redis_result.get("cal", {}))
            if self.redis_config.get("loss_enabled", False):
                self.registry.apply_redis_loss(redis_result.get("loss", {}))
        else:
            self.registry.apply_redis_cal(redis_result)
        self._refresh_table()

    @Slot(int, str)
    def _handle_redis_error(self, query_id: int, message: str) -> None:
        if query_id != self.redis_query_seq:
            return

        self.redis_query_in_flight = False
        self.redis_last_error = message or "Redis query failed"
        self.registry.mark_redis_down()
        self._refresh_table()

    def _record_export_frame(self, active_links: List[Dict[str, Any]]) -> None:
        if not self.exporter.is_active:
            return

        self.exporter.record_frame(self.current_time, self.calculator.satellites, active_links)
        if self.current_time >= self.exporter.end_time_ref:
            self.exporter.stop()

    def loop(self, advance: bool = True) -> None:
        if not self.calculator.satellites:
            return

        if advance:
            self.current_time += timedelta(seconds=self.step_size)

        self.calculator.propagate(self.current_time)
        sats = satellite_positions_array(self.calculator.satellites)

        self.registry.build_if_needed(self.strategy, self.calculator.satellites)

        isl, active_links = self.strategy.compute_links(self.calculator.satellites)
        self.registry.apply_active_links(active_links)
        self._schedule_redis_update_if_needed()
        self._record_export_frame(active_links)
        self._refresh_table()

        self.visualizer.update_scene(
            sats,
            isl,
            highlight_lines=link_pairs_to_lines(self.selected_link_pairs),
        )
        self.statusBar().showMessage(
            f"Satellites: {len(self.calculator.satellites)} | Active Links: {len(active_links)}"
        )

    def closeEvent(self, event) -> None:
        self.timer.stop()
        self.stop_redis_worker()
        super().closeEvent(event)
