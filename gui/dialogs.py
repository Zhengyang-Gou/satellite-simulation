"""Dialog classes used by MainWindow."""
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


def _configure_form_layout(layout: QFormLayout) -> None:
    layout.setContentsMargins(18, 18, 18, 18)
    layout.setHorizontalSpacing(14)
    layout.setVerticalSpacing(10)
    layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
    layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)


def _configure_box_layout(layout: QVBoxLayout) -> None:
    layout.setContentsMargins(18, 18, 18, 18)
    layout.setSpacing(12)


def _dialog_buttons(dialog: QDialog) -> QDialogButtonBox:
    btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    ok_button = btns.button(QDialogButtonBox.Ok)
    if ok_button is not None:
        ok_button.setText("确定")
        ok_button.setObjectName("primaryButton")
        ok_button.setDefault(True)
    cancel_button = btns.button(QDialogButtonBox.Cancel)
    if cancel_button is not None:
        cancel_button.setText("取消")
    btns.accepted.connect(dialog.accept)
    btns.rejected.connect(dialog.reject)
    return btns


class WalkerDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("生成 Walker 星座")
        self.setMinimumWidth(480)
        layout = QFormLayout(self)
        _configure_form_layout(layout)

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

        layout.addRow("卫星总数 (T)：", self.spin_t)
        layout.addRow("轨道面数 (P)：", self.spin_p)
        layout.addRow("相位因子 (F)：", self.spin_f)
        layout.addRow("轨道高度：", self.spin_alt)
        layout.addRow("轨道倾角：", self.spin_inc)

        layout.addRow(_dialog_buttons(self))


class TopologyDialog(QDialog):
    def __init__(
        self,
        latitude_fuse_enabled: bool = False,
        latitude_threshold: float = 70.0,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("网络拓扑设置")
        self.setMinimumWidth(480)

        layout = QVBoxLayout(self)
        _configure_box_layout(layout)

        strategy_label = QLabel("连接策略：Grid Delta")
        strategy_label.setObjectName("hintLabel")
        layout.addWidget(strategy_label)

        delta_group = QGroupBox("Delta 拓扑")
        delta_layout = QFormLayout(delta_group)
        _configure_form_layout(delta_layout)

        self.chk_latitude_fuse = QCheckBox("启用纬度熔断")
        self.chk_latitude_fuse.setChecked(latitude_fuse_enabled)

        self.spin_latitude_threshold = QDoubleSpinBox()
        self.spin_latitude_threshold.setRange(0.0, 90.0)
        self.spin_latitude_threshold.setDecimals(1)
        self.spin_latitude_threshold.setValue(latitude_threshold)
        self.spin_latitude_threshold.setSuffix(" °")

        delta_layout.addRow(self.chk_latitude_fuse)
        delta_layout.addRow("纬度阈值：", self.spin_latitude_threshold)
        layout.addWidget(delta_group)

        layout.addWidget(_dialog_buttons(self))


class LinkDatasetExportDialog(QDialog):
    def __init__(self, constellation_config: Dict[str, Any], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("导出链路状态数据集")
        self.setMinimumWidth(520)
        self.path = ""
        self.constellation_config = dict(constellation_config)

        layout = QVBoxLayout(self)
        _configure_box_layout(layout)

        constellation_group = QGroupBox("星座参数")
        constellation_layout = QFormLayout(constellation_group)
        _configure_form_layout(constellation_layout)

        constellation_layout.addRow(
            "卫星总数 (T)：",
            QLabel(str(self.constellation_config["total"])),
        )
        constellation_layout.addRow(
            "轨道面数：",
            QLabel(str(self.constellation_config["orbit_num"])),
        )
        constellation_layout.addRow(
            "每轨卫星数：",
            QLabel(str(self.constellation_config["sat_per_orbit"])),
        )
        constellation_layout.addRow(
            "相位因子 (F)：",
            QLabel(str(self.constellation_config["phase_factor"])),
        )
        constellation_layout.addRow(
            "轨道高度：",
            QLabel(f"{self.constellation_config['altitude_km']:.1f} km"),
        )
        constellation_layout.addRow(
            "轨道倾角：",
            QLabel(f"{self.constellation_config['inclination_deg']:.1f} °"),
        )
        layout.addWidget(constellation_group)

        simulation_group = QGroupBox("仿真参数")
        simulation_layout = QFormLayout(simulation_group)
        _configure_form_layout(simulation_layout)

        self.spin_time_slices = QSpinBox()
        self.spin_time_slices.setRange(1, 1_000_000)
        self.spin_time_slices.setValue(6000)

        self.spin_duration = QDoubleSpinBox()
        self.spin_duration.setRange(0.1, 31_536_000.0)
        self.spin_duration.setDecimals(1)
        self.spin_duration.setValue(6000.0)
        self.spin_duration.setSuffix(" s")

        simulation_layout.addRow("时间片数量：", self.spin_time_slices)
        simulation_layout.addRow("仿真总时长：", self.spin_duration)
        layout.addWidget(simulation_group)

        failure_group = QGroupBox("随机链路失效")
        failure_layout = QFormLayout(failure_group)
        _configure_form_layout(failure_layout)

        self.chk_random_failure = QCheckBox("启用随机链路失效")

        self.spin_failure_probability = QDoubleSpinBox()
        self.spin_failure_probability.setRange(0.0, 1.0)
        self.spin_failure_probability.setDecimals(6)
        self.spin_failure_probability.setSingleStep(0.01)
        self.spin_failure_probability.setValue(0.01)

        self.spin_random_seed = QSpinBox()
        self.spin_random_seed.setRange(0, 2_147_483_647)
        self.spin_random_seed.setValue(42)

        failure_layout.addRow(self.chk_random_failure)
        failure_layout.addRow("单片失效概率：", self.spin_failure_probability)
        failure_layout.addRow("随机种子：", self.spin_random_seed)
        layout.addWidget(failure_group)

        output_group = QGroupBox("输出")
        output_layout = QFormLayout(output_group)
        _configure_form_layout(output_layout)

        self.btn_path = QPushButton("选择目录...")
        self.btn_path.clicked.connect(self._select_directory)

        self.lbl_path = QLabel("未选择")
        self.lbl_path.setWordWrap(True)

        output_layout.addRow("保存到：", self.btn_path)
        output_layout.addRow("", self.lbl_path)
        layout.addWidget(output_group)

        layout.addWidget(_dialog_buttons(self))

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
    """Redis 与可选 SSH 隧道配置对话框。"""

    def __init__(self, config: Dict[str, Any], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Redis 连接设置")
        self.setMinimumWidth(600)
        self._config = dict(config)

        layout = QVBoxLayout(self)
        _configure_box_layout(layout)

        self.chk_enabled = QCheckBox("启用 Redis 查询")
        self.chk_enabled.setChecked(bool(self._config.get("enabled", False)))
        layout.addWidget(self.chk_enabled)

        redis_group = QGroupBox("Redis")
        redis_layout = QFormLayout(redis_group)
        _configure_form_layout(redis_layout)

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

        self.chk_loss_enabled = QCheckBox("启用丢包查询")
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

        redis_layout.addRow("Redis 主机：", self.txt_host)
        redis_layout.addRow("Redis 端口：", self.spin_port)
        redis_layout.addRow("Redis 数据库：", self.spin_db)
        redis_layout.addRow("Redis 密码：", self.txt_password)
        redis_layout.addRow("键名前缀：", self.txt_key_prefix)
        redis_layout.addRow(self.chk_loss_enabled)
        redis_layout.addRow("丢包缩放：", self.spin_loss_scale)
        redis_layout.addRow("连接超时：", self.spin_socket_timeout)

        layout.addWidget(redis_group)

        ssh_group = QGroupBox("SSH 隧道")
        ssh_layout = QFormLayout(ssh_group)
        _configure_form_layout(ssh_layout)

        self.chk_use_ssh = QCheckBox("使用 SSH 隧道")
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
        self.btn_ssh_private_key = QPushButton("浏览...")
        self.btn_ssh_private_key.clicked.connect(self._select_private_key)

        key_row = QHBoxLayout()
        key_row.addWidget(self.txt_ssh_private_key)
        key_row.addWidget(self.btn_ssh_private_key)

        self.txt_ssh_private_key_passphrase = QLineEdit(
            str(self._config.get("ssh_private_key_passphrase") or "")
        )
        self.txt_ssh_private_key_passphrase.setEchoMode(QLineEdit.Password)

        hint = QLabel(
            "SSH 模式下，Redis 主机和端口应填写远程服务器视角下的 Redis 地址。"
            "如果 Redis 只在该服务器本机监听，通常填写 127.0.0.1:6379。"
        )
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignLeft)
        hint.setObjectName("hintLabel")

        ssh_layout.addRow(self.chk_use_ssh)
        ssh_layout.addRow("SSH 主机：", self.txt_ssh_host)
        ssh_layout.addRow("SSH 端口：", self.spin_ssh_port)
        ssh_layout.addRow("SSH 用户名：", self.txt_ssh_username)
        ssh_layout.addRow("SSH 密码：", self.txt_ssh_password)
        ssh_layout.addRow("私钥文件：", key_row)
        ssh_layout.addRow("私钥口令：", self.txt_ssh_private_key_passphrase)
        ssh_layout.addRow(hint)

        layout.addWidget(ssh_group)

        btn_row = QHBoxLayout()
        self.btn_test = QPushButton("测试连接")
        self.btn_test.clicked.connect(self._test_connection)
        btn_row.addWidget(self.btn_test)
        btn_row.addStretch()

        self.btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok_button = self.btns.button(QDialogButtonBox.Ok)
        if ok_button is not None:
            ok_button.setText("确定")
            ok_button.setObjectName("primaryButton")
            ok_button.setDefault(True)
        cancel_button = self.btns.button(QDialogButtonBox.Cancel)
        if cancel_button is not None:
            cancel_button.setText("取消")
        self.btns.accepted.connect(self.accept)
        self.btns.rejected.connect(self.reject)
        btn_row.addWidget(self.btns)

        layout.addLayout(btn_row)
        self._update_ssh_enabled(self.chk_use_ssh.isChecked())

    def _select_private_key(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "选择 SSH 私钥", "", "所有文件 (*)")
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
                QMessageBox.warning(self, "Redis 设置", "启用 SSH 隧道时必须填写 SSH 主机。")
                return
            if not cfg["ssh_username"]:
                QMessageBox.warning(self, "Redis 设置", "启用 SSH 隧道时必须填写 SSH 用户名。")
                return
            if not cfg["ssh_password"] and not cfg["ssh_private_key"]:
                QMessageBox.warning(
                    self,
                    "Redis 设置",
                    "启用 SSH 隧道时，请提供 SSH 密码或 SSH 私钥。",
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
            QMessageBox.information(self, "Redis 测试", message)
        else:
            QMessageBox.warning(self, "Redis 测试失败", message)
