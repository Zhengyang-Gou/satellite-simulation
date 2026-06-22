"""Background worker for one remote measurement time slice."""

from __future__ import annotations

import subprocess
import time
from typing import Optional
import os
import signal

from PySide6.QtCore import QObject, Signal, Slot

from .config import (
    DEFAULT_REDIS_PASSWORD_FILE,
    DEFAULT_REMOTE_COMMAND_TIMEOUT_SEC,
    DEFAULT_REMOTE_MEASURE_SCRIPT,
    DEFAULT_REMOTE_PROBE_COUNT,
    DEFAULT_REMOTE_PROBE_PPS,
)


class RemoteMeasureSliceWorker(QObject):
    """Execute one remote measure_slice.sh transaction."""

    finished = Signal(int, bool, str, float)

    def __init__(
        self,
        *,
        time_slice: int,
        ssh_host_alias: str = "satellite-simulation",
        remote_script: str = DEFAULT_REMOTE_MEASURE_SCRIPT,
        probe_count: int = DEFAULT_REMOTE_PROBE_COUNT,
        probe_pps: float = DEFAULT_REMOTE_PROBE_PPS,
        timeout_sec: float = DEFAULT_REMOTE_COMMAND_TIMEOUT_SEC,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self.time_slice = int(time_slice)
        self.ssh_host_alias = ssh_host_alias
        self.remote_script = remote_script
        self.probe_count = int(probe_count)
        self.probe_pps = float(probe_pps)
        self.timeout_sec = float(timeout_sec)
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
            (
                f"sudo -S -p '' timeout {self.timeout_sec:g}s bash {self.remote_script} "
                f"{self.time_slice} {self.probe_count} {self.probe_pps:g}"
            ),
        ]

        started_at = time.monotonic()
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
                timeout=self.timeout_sec + 1.0,
            )
            returncode = self._process.returncode
        except subprocess.TimeoutExpired as exc:
            self.cancel()
            elapsed = time.monotonic() - started_at
            output = (exc.stdout or "").strip() if isinstance(exc.stdout, str) else ""
            message = output or f"时间片 {self.time_slice} 远端测量超过 {self.timeout_sec:g}s"
            self.finished.emit(self.time_slice, False, message, elapsed)
            return
        except Exception as exc:
            elapsed = time.monotonic() - started_at
            if self._cancelled:
                self.finished.emit(self.time_slice, False, f"时间片 {self.time_slice} 已取消", elapsed)
            else:
                self.finished.emit(self.time_slice, False, f"时间片 {self.time_slice} 启动失败：{exc}", elapsed)
            return
        finally:
            self._process = None

        elapsed = time.monotonic() - started_at
        output = (output or "").strip()
        if self._cancelled:
            self.finished.emit(self.time_slice, False, f"时间片 {self.time_slice} 已取消", elapsed)
        elif returncode == 0:
            self.finished.emit(self.time_slice, True, output or f"时间片 {self.time_slice} 完成", elapsed)
        else:
            self.finished.emit(
                self.time_slice,
                False,
                output or f"时间片 {self.time_slice} 失败，退出码 {returncode}",
                elapsed,
            )

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
