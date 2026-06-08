"""Dialog classes used by MainWindow."""

import os
from typing import Any, Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
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
    def __init__(
        self,
        latitude_fuse_enabled: bool = False,
        latitude_threshold: float = 70.0,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Network Topology Settings")
        self.setMinimumWidth(350)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Connection Strategy: +Grid（Delta）"))

        delta_group = QGroupBox("Delta")
        delta_layout = QFormLayout(delta_group)

        self.chk_latitude_fuse = QCheckBox("Enable Latitude Fuse")
        self.chk_latitude_fuse.setChecked(latitude_fuse_enabled)

        self.spin_latitude_threshold = QDoubleSpinBox()
        self.spin_latitude_threshold.setRange(0.0, 90.0)
        self.spin_latitude_threshold.setDecimals(1)
        self.spin_latitude_threshold.setValue(latitude_threshold)
        self.spin_latitude_threshold.setSuffix(" °")

        delta_layout.addRow(self.chk_latitude_fuse)
        delta_layout.addRow("Latitude Threshold:", self.spin_latitude_threshold)
        layout.addWidget(delta_group)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)


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


class LinkDatasetExportDialog(QDialog):
    def __init__(self, constellation_config: Dict[str, Any], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Export Link State Dataset")
        self.setMinimumWidth(460)
        self.path = ""
        self.constellation_config = dict(constellation_config)

        layout = QVBoxLayout(self)

        constellation_group = QGroupBox("Constellation")
        constellation_layout = QFormLayout(constellation_group)

        constellation_layout.addRow(
            "Total Satellites (T):",
            QLabel(str(self.constellation_config["total"])),
        )
        constellation_layout.addRow(
            "Orbit Num:",
            QLabel(str(self.constellation_config["orbit_num"])),
        )
        constellation_layout.addRow(
            "Satellites Per Orbit:",
            QLabel(str(self.constellation_config["sat_per_orbit"])),
        )
        constellation_layout.addRow(
            "Phase Factor (F):",
            QLabel(str(self.constellation_config["phase_factor"])),
        )
        constellation_layout.addRow(
            "Altitude:",
            QLabel(f"{self.constellation_config['altitude_km']:.1f} km"),
        )
        constellation_layout.addRow(
            "Inclination:",
            QLabel(f"{self.constellation_config['inclination_deg']:.1f} °"),
        )
        layout.addWidget(constellation_group)

        simulation_group = QGroupBox("Simulation")
        simulation_layout = QFormLayout(simulation_group)

        self.spin_time_slices = QSpinBox()
        self.spin_time_slices.setRange(1, 1_000_000)
        self.spin_time_slices.setValue(6000)

        self.spin_duration = QDoubleSpinBox()
        self.spin_duration.setRange(0.1, 31_536_000.0)
        self.spin_duration.setDecimals(1)
        self.spin_duration.setValue(6000.0)
        self.spin_duration.setSuffix(" s")

        simulation_layout.addRow("Time Slices:", self.spin_time_slices)
        simulation_layout.addRow("Simulation Duration:", self.spin_duration)
        layout.addWidget(simulation_group)

        failure_group = QGroupBox("Random Link Failure")
        failure_layout = QFormLayout(failure_group)

        self.chk_random_failure = QCheckBox("Enable Random Link Failure")

        self.spin_failure_probability = QDoubleSpinBox()
        self.spin_failure_probability.setRange(0.0, 1.0)
        self.spin_failure_probability.setDecimals(6)
        self.spin_failure_probability.setSingleStep(0.01)
        self.spin_failure_probability.setValue(0.01)

        self.spin_random_seed = QSpinBox()
        self.spin_random_seed.setRange(0, 2_147_483_647)
        self.spin_random_seed.setValue(42)

        failure_layout.addRow(self.chk_random_failure)
        failure_layout.addRow("Down Probability / Slice:", self.spin_failure_probability)
        failure_layout.addRow("Random Seed:", self.spin_random_seed)
        layout.addWidget(failure_group)

        output_group = QGroupBox("Output")
        output_layout = QFormLayout(output_group)

        self.btn_path = QPushButton("Select Directory...")
        self.btn_path.clicked.connect(self._select_directory)

        self.lbl_path = QLabel("Not Selected")
        self.lbl_path.setWordWrap(True)

        output_layout.addRow("Save To:", self.btn_path)
        output_layout.addRow("", self.lbl_path)
        layout.addWidget(output_group)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _select_directory(self) -> None:
        directory = QFileDialog.getExistingDirectory(self)
        if directory:
            self.path = directory
            self.lbl_path.setText(directory)

    def config(self) -> Dict[str, Any]:
        return {
            "time_slices": self.spin_time_slices.value(),
            "duration_sec": self.spin_duration.value(),
            "random_failure_enabled": self.chk_random_failure.isChecked(),
            "failure_probability": self.spin_failure_probability.value(),
            "random_seed": self.spin_random_seed.value(),
            "output_dir": self.path,
        }


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

        self.chk_loss_enabled = QCheckBox("Enable Loss Query")
        self.chk_loss_enabled.setChecked(bool(self._config.get("loss_enabled", False)))

        self.spin_loss_scale = QDoubleSpinBox()
        self.spin_loss_scale.setRange(0.000001, 1_000_000_000.0)
        self.spin_loss_scale.setDecimals(6)
        self.spin_loss_scale.setValue(float(self._config.get("loss_scale") or 1.0))

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
        redis_layout.addRow(self.chk_loss_enabled)
        redis_layout.addRow("Loss Scale:", self.spin_loss_scale)
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
            "loss_enabled": self.chk_loss_enabled.isChecked(),
            "loss_scale": self.spin_loss_scale.value(),
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
