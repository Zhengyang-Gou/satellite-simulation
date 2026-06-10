"""Main application window after modularizing UI, table, topology, and Redis concerns."""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Set

from PySide6.QtCore import QSize, Qt, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QInputDialog,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QSplitter,
    QStyle,
    QToolBar,
    QVBoxLayout,
    QWidget,
)
from core.calculator import OrbitCalculator
from core.link_dataset_exporter import LinkDatasetExportCancelled, LinkDatasetExporter
from core.strategies import GridDeltaStrategy

from .config import env_int, redis_config_from_env
from .dialogs import (
    LinkDatasetExportDialog,
    RedisSettingsDialog,
    TopologyDialog,
    WalkerDialog,
)
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

        self.setWindowTitle("Satellite Simulation")
        self.resize(1200, 900)
        self.setStyleSheet(DARK_THEME)

        self.calculator = OrbitCalculator()
        self.strategy = GridDeltaStrategy()
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
        self.current_walker_config: Optional[Dict[str, Any]] = None

        self._init_ui()
        self._init_menu()
        self._init_toolbar()
        self.statusBar().showMessage("就绪")

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

        m_data = mb.addMenu("数据")
        self.act_load_tle = QAction("加载 TLE", self)
        self.act_load_tle.triggered.connect(self.load_tle_file)

        self.act_generate_walker = QAction("生成 Walker 星座", self)
        self.act_generate_walker.triggered.connect(self.open_walker_gen)

        m_data.addAction(self.act_load_tle)
        m_data.addAction(self.act_generate_walker)

        m_topo = mb.addMenu("拓扑")
        self.act_topology = QAction("拓扑设置", self)
        self.act_topology.triggered.connect(self.open_topology_settings)
        m_topo.addAction(self.act_topology)

        m_sim = mb.addMenu("仿真")

        self.act_play = QAction("开始", self)
        self.act_play.triggered.connect(self.toggle_sim)
        self.act_play.setEnabled(False)

        self.act_step = QAction("步长设置", self)
        self.act_step.triggered.connect(self.open_step_settings)

        self.act_export_dataset = QAction("导出数据集", self)
        self.act_export_dataset.triggered.connect(self.open_link_dataset_export)

        m_sim.addAction(self.act_play)
        m_sim.addAction(self.act_step)
        m_sim.addSeparator()
        m_sim.addAction(self.act_export_dataset)

        m_redis = mb.addMenu("Redis")

        self.act_redis_enable = QAction("启用 Redis 查询", self)
        self.act_redis_enable.setCheckable(True)
        self.act_redis_enable.setChecked(self.redis_enabled)
        self.act_redis_enable.toggled.connect(self.toggle_redis_query)

        m_redis.addAction(self.act_redis_enable)
        self.act_redis_settings = QAction("Redis 设置", self)
        self.act_redis_settings.triggered.connect(self.open_redis_settings)
        m_redis.addAction(self.act_redis_settings)

    def _init_toolbar(self) -> None:
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(18, 18))
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        style = self.style()
        self.act_load_tle.setIcon(style.standardIcon(QStyle.SP_DialogOpenButton))
        self.act_generate_walker.setIcon(style.standardIcon(QStyle.SP_FileDialogNewFolder))
        self.act_play.setIcon(style.standardIcon(QStyle.SP_MediaPlay))
        self.act_step.setIcon(style.standardIcon(QStyle.SP_BrowserReload))
        self.act_export_dataset.setIcon(style.standardIcon(QStyle.SP_DriveHDIcon))
        self.act_redis_enable.setIcon(style.standardIcon(QStyle.SP_DriveNetIcon))
        self.act_redis_settings.setIcon(style.standardIcon(QStyle.SP_FileDialogDetailedView))

        toolbar.addAction(self.act_load_tle)
        toolbar.addAction(self.act_generate_walker)
        toolbar.addSeparator()
        toolbar.addAction(self.act_play)
        toolbar.addAction(self.act_step)
        toolbar.addAction(self.act_export_dataset)
        toolbar.addSeparator()
        toolbar.addAction(self.act_redis_enable)
        toolbar.addAction(self.act_redis_settings)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

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
        phase_factor = dlg.spin_f.value()
        altitude_km = dlg.spin_alt.value()
        inclination_deg = dlg.spin_inc.value()

        if total % planes != 0:
            QMessageBox.warning(
                self,
                "Walker 参数错误",
                "卫星总数 (T) 必须能被轨道面数 (P) 整除。",
            )
            return

        count = self.calculator.generate_walker(
            total,
            planes,
            phase_factor,
            altitude_km,
            inclination_deg,
            self.current_time,
        )

        if count:
            self.current_walker_config = {
                "total": total,
                "orbit_num": planes,
                "sat_per_orbit": total // planes,
                "phase_factor": phase_factor,
                "altitude_km": altitude_km,
                "inclination_deg": inclination_deg,
                "epoch_time": self.current_time,
            }
            self.reset_simulation_state()
            self.act_play.setEnabled(True)
            self.loop(advance=False)

    def open_topology_settings(self) -> None:
        dlg = TopologyDialog(
            latitude_fuse_enabled=getattr(self.strategy, "latitude_fuse_enabled", False),
            latitude_threshold=getattr(self.strategy, "latitude_threshold", 70.0),
            parent=self,
        )
        if dlg.exec() != QDialog.Accepted:
            return

        self.strategy = GridDeltaStrategy(
            latitude_fuse_enabled=dlg.chk_latitude_fuse.isChecked(),
            latitude_threshold=dlg.spin_latitude_threshold.value(),
        )

        self.reset_simulation_state()
        if self.calculator.satellites:
            self.loop(advance=False)

    def open_step_settings(self) -> None:
        value, ok = QInputDialog.getDouble(
            self,
            "设置步长",
            "请输入每次推进的仿真步长，单位秒：",
            self.step_size,
            0.1,
            3600.0,
            1,
        )
        if ok:
            self.step_size = value

    def open_link_dataset_export(self) -> None:
        export_error = self._walker_dataset_export_error()
        if export_error:
            QMessageBox.warning(
                self,
                "导出数据集",
                export_error,
            )
            return

        dlg = LinkDatasetExportDialog(self.current_walker_config, self)
        if dlg.exec() != QDialog.Accepted:
            return

        config = dlg.config()
        if not config["output_dir"]:
            QMessageBox.warning(self, "导出数据集", "请选择输出目录。")
            return

        progress = QProgressDialog(
            "正在生成链路状态数据集...",
            "取消",
            0,
            config["time_slices"],
            self,
        )
        progress.setWindowTitle("导出链路状态数据集")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)

        def report_progress(done: int, total: int) -> bool:
            progress.setMaximum(total)
            progress.setValue(done)
            QApplication.processEvents()
            return not progress.wasCanceled()

        try:
            result = LinkDatasetExporter().export(
                orbit_num=self.current_walker_config["orbit_num"],
                sat_per_orbit=self.current_walker_config["sat_per_orbit"],
                time_slices=config["time_slices"],
                duration_sec=config["duration_sec"],
                output_dir=config["output_dir"],
                phase_factor=self.current_walker_config["phase_factor"],
                altitude_km=self.current_walker_config["altitude_km"],
                inclination_deg=self.current_walker_config["inclination_deg"],
                random_failure_enabled=config["random_failure_enabled"],
                failure_probability=config["failure_probability"],
                random_seed=config["random_seed"],
                strategy=self._clone_strategy(),
                start_time=self.current_time,
                epoch_time=self.current_walker_config["epoch_time"],
                progress_callback=report_progress,
            )
        except LinkDatasetExportCancelled:
            QMessageBox.information(self, "导出数据集", "导出已取消。")
            return
        except Exception as exc:
            QMessageBox.warning(self, "导出数据集", f"导出失败：\n{exc}")
            return
        finally:
            progress.close()

        QMessageBox.information(
            self,
            "导出数据集",
            (
                f"已生成 {result.file_count} 个卫星文件，"
                f"每个文件包含 {result.time_slices} 个时间片。\n\n{result.output_dir}"
            ),
        )

    def _has_walker_constellation(self) -> bool:
        return bool(
            self.calculator.satellites
            and getattr(self.calculator.satellites[0], "is_walker", False)
        )

    def _walker_dataset_export_error(self) -> str:
        if not self.current_walker_config or not self._has_walker_constellation():
            return "请先生成 Walker 星座，再导出链路状态数据集。"

        orbit_num = self.current_walker_config["orbit_num"]
        sat_per_orbit = self.current_walker_config["sat_per_orbit"]
        if orbit_num < 3 or sat_per_orbit < 3:
            return (
                "当前数据集格式要求 Walker 星座至少包含 3 个轨道面，"
                "且每个轨道面至少包含 3 颗卫星。"
            )
        if orbit_num > 99 or sat_per_orbit > 99:
            return (
                "当前数据集格式要求轨道面数量和每轨卫星数量均不超过 99，"
                "以便生成两位编号。"
            )
        return ""

    def _clone_strategy(self):
        return GridDeltaStrategy(
            latitude_fuse_enabled=getattr(self.strategy, "latitude_fuse_enabled", False),
            latitude_threshold=getattr(self.strategy, "latitude_threshold", 70.0),
        )

    def load_tle_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "打开 TLE 文件", "", "TLE 文件 (*.txt *.tle)")
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                count = self.calculator.load_tle_data(file.read())
        except UnicodeDecodeError:
            with open(file_path, "r", encoding="latin-1") as file:
                count = self.calculator.load_tle_data(file.read())
        except OSError as exc:
            QMessageBox.warning(self, "加载 TLE", f"打开文件失败：\n{exc}")
            return

        if count:
            self.current_walker_config = None
            self.reset_simulation_state()
            self.act_play.setEnabled(True)
            self.loop(advance=False)
        else:
            QMessageBox.warning(self, "加载 TLE", "未从该 TLE 文件中加载到有效卫星。")

    def toggle_sim(self) -> None:
        self.is_playing = not self.is_playing
        self.act_play.setText("暂停" if self.is_playing else "开始")
        self.act_play.setIcon(
            self.style().standardIcon(QStyle.SP_MediaPause if self.is_playing else QStyle.SP_MediaPlay)
        )

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
        self.redis_last_error = message or "Redis 查询失败"
        self.registry.mark_redis_down()
        self._refresh_table()

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
        self._refresh_table()

        self.visualizer.update_scene(
            sats,
            isl,
            highlight_lines=link_pairs_to_lines(self.selected_link_pairs),
        )
        self.visualizer.update_hud(
            satellite_count=len(self.calculator.satellites),
            active_link_count=len(active_links),
            current_time=self.current_time,
            redis_status=self._redis_status_text(),
        )
        self.statusBar().showMessage(
            f"卫星：{len(self.calculator.satellites)} | 活动链路：{len(active_links)}"
        )

    def _redis_status_text(self) -> str:
        if self.redis_last_error:
            return "异常"
        if self.redis_query_in_flight:
            return "更新中"
        if self.redis_enabled:
            return "已启用"
        return "空闲"

    def closeEvent(self, event) -> None:
        self.timer.stop()
        self.stop_redis_worker()
        super().closeEvent(event)
