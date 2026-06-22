"""Background worker for remote one-click deployment."""

from __future__ import annotations

import os
import signal
import subprocess
from typing import Optional

from PySide6.QtCore import QObject, Signal, Slot

from .config import DEFAULT_REDIS_PASSWORD_FILE


class RemoteDeployWorker(QObject):
    """Run the remote deployment script without blocking the GUI thread."""

    finished = Signal(bool, str)

    def __init__(
        self,
        *,
        ssh_host_alias: str = "satellite-simulation",
        remote_script: str = "/home/s223/yzy/scripts/deploy.sh",
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self.ssh_host_alias = ssh_host_alias
        self.remote_script = remote_script
        self._process: Optional[subprocess.Popen[str]] = None
        self._cancelled = False

    @Slot()
    def run(self) -> None:
        password = self._read_sudo_password()
        command = [
            "ssh",
            "-o",
            "BatchMode=yes",
            self.ssh_host_alias,
            f"sudo -S -p '' bash {self.remote_script}",
        ]

        try:
            self._process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                start_new_session=True,
            )
            output, _ = self._process.communicate(
                input=f"{password}\n" if password else "\n",
            )
        except Exception as exc:
            if self._cancelled:
                self.finished.emit(False, "Deploy 已取消")
            else:
                self.finished.emit(False, f"Deploy 启动失败：{exc}")
            return
        finally:
            process = self._process
            self._process = None

        returncode = process.returncode if process is not None else 1
        output = (output or "").strip()
        if self._cancelled:
            self.finished.emit(False, "Deploy 已取消")
        elif returncode == 0:
            self.finished.emit(True, output or "部署完成")
        else:
            self.finished.emit(False, output or f"Deploy 失败，退出码 {returncode}")

    @Slot()
    def cancel(self) -> None:
        self._cancelled = True
        process = self._process
        if process is None or process.poll() is not None:
            return
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except Exception:
            process.terminate()
        try:
            process.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except Exception:
                process.kill()

    def _read_sudo_password(self) -> str:
        try:
            with open(DEFAULT_REDIS_PASSWORD_FILE, encoding="utf-8") as password_file:
                return password_file.read().strip()
        except OSError:
            return ""
