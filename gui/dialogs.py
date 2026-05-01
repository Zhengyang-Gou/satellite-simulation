"""Dialog classes used by MainWindow."""

import os
from typing import Any, Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class WalkerDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Generate Walker Constellation")
        layout = QFormLayout(self)

        self.spin_t = QSpinBox()
        self.spin_t.setRange(1, 10000)
        self.spin_t.setValue(525)

        self.spin_p = QSpinBox()
        self.spin_p.setRange(1, 1000)
        self.spin_p.setValue(15)

        self.spin_f = QSpinBox()
        self.spin_f.setRange(0, 1000)
        self.spin_f.setValue(0)

        self.spin_alt = QDoubleSpinBox()
        self.spin_alt.setRange(100, 20000)
        self.spin_alt.setValue(550.0)
        self.spin_alt.setSuffix(" km")

        self.spin_inc = QDoubleSpinBox()
        self.spin_inc.setRange(0, 180)
        self.spin_inc.setValue(53.0)
        self.spin_inc.setSuffix(" °")

        layout.addRow("Total Satellites (T):", self.spin_t)
        layout.addRow("Orbital Planes (P):", self.spin_p)
        layout.addRow("Phase Factor (F):", self.spin_f)
        layout.addRow("Altitude:", self.spin_alt)
        layout.addRow("Inclination:", self.spin_inc)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)


class TopologyDialog(QDialog):
    def __init__(self, current_strategy_idx: int, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Network Topology Settings")
        self.setMinimumWidth(350)

        layout = QVBoxLayout(self)

        self.combo_strat = QComboBox()
        self.combo_strat.addItems(["+Grid（Star）", "+Grid（Delta）"])
        self.combo_strat.setCurrentIndex(current_strategy_idx)

        layout.addWidget(QLabel("Connection Strategy:"))
        layout.addWidget(self.combo_strat)

        self.panel_mesh = QWidget()
        l_mesh = QFormLayout(self.panel_mesh)

        self.spin_plane_tol = QDoubleSpinBox()
        self.spin_plane_tol.setValue(6.0)
        self.spin_plane_tol.setSuffix(" °")

        self.spin_intra = QSpinBox()
        self.spin_intra.setRange(0, 10000)
        self.spin_intra.setValue(5000)
        self.spin_intra.setSuffix(" km")

        self.spin_inter = QSpinBox()
        self.spin_inter.setRange(0, 10000)
        self.spin_inter.setValue(5000)
        self.spin_inter.setSuffix(" km")

        self.chk_polar = QCheckBox("Enable Polar Cut")
        self.chk_polar.setChecked(True)

        self.spin_polar_lat = QDoubleSpinBox()
        self.spin_polar_lat.setRange(0, 90)
        self.spin_polar_lat.setValue(70.0)
        self.spin_polar_lat.setSuffix(" °")

        l_mesh.addRow("Plane Tolerance:", self.spin_plane_tol)
        l_mesh.addRow("Max Intra-plane Dist:", self.spin_intra)
        l_mesh.addRow("Max Inter-plane Dist:", self.spin_inter)
        l_mesh.addRow(self.chk_polar)
        l_mesh.addRow("Cutoff Latitude:", self.spin_polar_lat)

        self.panel_delta = QWidget()
        l_delta = QFormLayout(self.panel_delta)

        self.spin_delta_lat = QDoubleSpinBox()
        self.spin_delta_lat.setRange(0, 90)
        self.spin_delta_lat.setValue(70.0)
        self.spin_delta_lat.setSuffix(" °")
        l_delta.addRow("Turnaround Latitude:", self.spin_delta_lat)

        layout.addWidget(self.panel_mesh)
        layout.addWidget(self.panel_delta)

        self.combo_strat.currentIndexChanged.connect(self.update_panels)
        self.update_panels(current_strategy_idx)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def update_panels(self, idx: int) -> None:
        self.panel_mesh.setVisible(idx == 0)
        self.panel_delta.setVisible(idx == 1)


class ExportDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Export Data Settings")
        layout = QFormLayout(self)

        self.path = ""
        self.btn_path = QPushButton("Select Directory...")
        self.lbl_path = QLabel("Not Selected")
        self.btn_path.clicked.connect(self._select_directory)

        self.spin_duration = QSpinBox()
        self.spin_duration.setRange(10, 36000)
        self.spin_duration.setValue(60)
        self.spin_duration.setSuffix(" s")

        layout.addRow("Save To:", self.btn_path)
        layout.addRow("", self.lbl_path)
        layout.addRow("Export Duration:", self.spin_duration)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

    def _select_directory(self) -> None:
        directory = QFileDialog.getExistingDirectory(self)
        if directory:
            self.path = directory
            self.lbl_path.setText(os.path.basename(directory) or directory)


class RedisSettingsDialog(QDialog):
    """Redis + optional SSH tunnel configuration dialog."""

    def __init__(self, config: Dict[str, Any], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Redis Connection Settings")
        self.setMinimumWidth(560)
        self._config = dict(config)

        layout = QVBoxLayout(self)

        self.chk_enabled = QCheckBox("Enable Redis Query")
        self.chk_enabled.setChecked(bool(self._config.get("enabled", False)))
        layout.addWidget(self.chk_enabled)

        redis_group = QGroupBox("Redis")
        redis_layout = QFormLayout(redis_group)

        self.txt_host = QLineEdit(str(self._config.get("host") or "127.0.0.1"))

        self.spin_port = QSpinBox()
        self.spin_port.setRange(1, 65535)
        self.spin_port.setValue(int(self._config.get("port") or 6379))

        self.spin_db = QSpinBox()
        self.spin_db.setRange(0, 999)
        self.spin_db.setValue(int(self._config.get("db") or 0))

        self.txt_password = QLineEdit(str(self._config.get("password") or ""))
        self.txt_password.setEchoMode(QLineEdit.Password)

        self.txt_key_prefix = QLineEdit(str(self._config.get("key_prefix") or "link"))

        self.spin_delay_scale = QDoubleSpinBox()
        self.spin_delay_scale.setRange(0.000001, 1_000_000_000.0)
        self.spin_delay_scale.setDecimals(6)
        self.spin_delay_scale.setValue(float(self._config.get("delay_scale") or 1000.0))

        self.spin_socket_timeout = QDoubleSpinBox()
        self.spin_socket_timeout.setRange(0.01, 60.0)
        self.spin_socket_timeout.setDecimals(3)
        self.spin_socket_timeout.setValue(float(self._config.get("socket_timeout") or 0.05))
        self.spin_socket_timeout.setSuffix(" s")

        redis_layout.addRow("Redis Host:", self.txt_host)
        redis_layout.addRow("Redis Port:", self.spin_port)
        redis_layout.addRow("Redis DB:", self.spin_db)
        redis_layout.addRow("Redis Password:", self.txt_password)
        redis_layout.addRow("Key Prefix:", self.txt_key_prefix)
        redis_layout.addRow("Delay Scale:", self.spin_delay_scale)
        redis_layout.addRow("Socket Timeout:", self.spin_socket_timeout)

        layout.addWidget(redis_group)

        ssh_group = QGroupBox("SSH Tunnel")
        ssh_layout = QFormLayout(ssh_group)

        self.chk_use_ssh = QCheckBox("Use SSH Tunnel")
        self.chk_use_ssh.setChecked(bool(self._config.get("use_ssh", False)))
        self.chk_use_ssh.toggled.connect(self._update_ssh_enabled)

        self.txt_ssh_host = QLineEdit(str(self._config.get("ssh_host") or ""))

        self.spin_ssh_port = QSpinBox()
        self.spin_ssh_port.setRange(1, 65535)
        self.spin_ssh_port.setValue(int(self._config.get("ssh_port") or 22))

        self.txt_ssh_username = QLineEdit(str(self._config.get("ssh_username") or ""))

        self.txt_ssh_password = QLineEdit(str(self._config.get("ssh_password") or ""))
        self.txt_ssh_password.setEchoMode(QLineEdit.Password)

        self.txt_ssh_private_key = QLineEdit(str(self._config.get("ssh_private_key") or ""))
        self.btn_ssh_private_key = QPushButton("Browse...")
        self.btn_ssh_private_key.clicked.connect(self._select_private_key)

        key_row = QHBoxLayout()
        key_row.addWidget(self.txt_ssh_private_key)
        key_row.addWidget(self.btn_ssh_private_key)

        self.txt_ssh_private_key_passphrase = QLineEdit(
            str(self._config.get("ssh_private_key_passphrase") or "")
        )
        self.txt_ssh_private_key_passphrase.setEchoMode(QLineEdit.Password)

        hint = QLabel(
            "SSH mode: Redis Host/Port should be the Redis address as seen from the remote server. "
            "For a private Redis service on that server, usually use 127.0.0.1:6379."
        )
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignLeft)

        ssh_layout.addRow(self.chk_use_ssh)
        ssh_layout.addRow("SSH Host:", self.txt_ssh_host)
        ssh_layout.addRow("SSH Port:", self.spin_ssh_port)
        ssh_layout.addRow("SSH Username:", self.txt_ssh_username)
        ssh_layout.addRow("SSH Password:", self.txt_ssh_password)
        ssh_layout.addRow("Private Key:", key_row)
        ssh_layout.addRow("Key Passphrase:", self.txt_ssh_private_key_passphrase)
        ssh_layout.addRow(hint)

        layout.addWidget(ssh_group)

        btn_row = QHBoxLayout()
        self.btn_test = QPushButton("Test Connection")
        self.btn_test.clicked.connect(self._test_connection)
        btn_row.addWidget(self.btn_test)
        btn_row.addStretch()

        self.btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.btns.accepted.connect(self.accept)
        self.btns.rejected.connect(self.reject)
        btn_row.addWidget(self.btns)

        layout.addLayout(btn_row)
        self._update_ssh_enabled(self.chk_use_ssh.isChecked())

    def _select_private_key(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Select SSH Private Key", "", "All Files (*)")
        if file_path:
            self.txt_ssh_private_key.setText(file_path)

    def _update_ssh_enabled(self, enabled: bool) -> None:
        widgets = [
            self.txt_ssh_host,
            self.spin_ssh_port,
            self.txt_ssh_username,
            self.txt_ssh_password,
            self.txt_ssh_private_key,
            self.btn_ssh_private_key,
            self.txt_ssh_private_key_passphrase,
        ]
        for widget in widgets:
            widget.setEnabled(enabled)

    def _clean_text(self, line_edit: QLineEdit) -> Optional[str]:
        value = line_edit.text().strip()
        return value or None

    def config(self) -> Dict[str, Any]:
        return {
            "enabled": self.chk_enabled.isChecked(),
            "host": self.txt_host.text().strip() or "127.0.0.1",
            "port": self.spin_port.value(),
            "password": self._clean_text(self.txt_password),
            "db": self.spin_db.value(),
            "key_prefix": self.txt_key_prefix.text().strip() or "link",
            "delay_scale": self.spin_delay_scale.value(),
            "socket_timeout": self.spin_socket_timeout.value(),
            "use_ssh": self.chk_use_ssh.isChecked(),
            "ssh_host": self._clean_text(self.txt_ssh_host),
            "ssh_port": self.spin_ssh_port.value(),
            "ssh_username": self._clean_text(self.txt_ssh_username),
            "ssh_password": self._clean_text(self.txt_ssh_password),
            "ssh_private_key": self._clean_text(self.txt_ssh_private_key),
            "ssh_private_key_passphrase": self._clean_text(self.txt_ssh_private_key_passphrase),
        }

    def accept(self) -> None:
        cfg = self.config()

        if cfg["enabled"] and cfg["use_ssh"]:
            if not cfg["ssh_host"]:
                QMessageBox.warning(self, "Redis Settings", "SSH Host is required when SSH tunnel is enabled.")
                return
            if not cfg["ssh_username"]:
                QMessageBox.warning(self, "Redis Settings", "SSH Username is required when SSH tunnel is enabled.")
                return
            if not cfg["ssh_password"] and not cfg["ssh_private_key"]:
                QMessageBox.warning(
                    self,
                    "Redis Settings",
                    "Provide either an SSH password or an SSH private key when SSH tunnel is enabled.",
                )
                return

        super().accept()

    def _test_connection(self) -> None:
        cfg = self.config()
        cfg["enabled"] = True

        try:
            from core.redis_latency import RedisLatencyProvider

            provider = RedisLatencyProvider(**cfg)
            ok, message = provider.test_connection()
            provider.close()
        except Exception as exc:
            ok = False
            message = str(exc)

        if ok:
            QMessageBox.information(self, "Redis Test", message)
        else:
            QMessageBox.warning(self, "Redis Test Failed", message)
