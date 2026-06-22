"""Runtime configuration helpers for the GUI layer."""

import os
from typing import Any, Dict, Optional


DEFAULT_REDIS_HOST = "127.0.0.1"
DEFAULT_REDIS_PORT = 6379
DEFAULT_REDIS_DB = 0
DEFAULT_REDIS_KEY_PREFIX = "data"
DEFAULT_REDIS_LOSS_ENABLED = True
DEFAULT_REDIS_LOSS_SCALE = 1.0
DEFAULT_REDIS_SOCKET_TIMEOUT = 0.05
DEFAULT_REMOTE_MEASURE_SCRIPT = "/home/s223/yzy/scripts/measure_slice.sh"
DEFAULT_REMOTE_PROBE_COUNT = 5
DEFAULT_REMOTE_PROBE_PPS = 10.0
DEFAULT_REMOTE_SLICE_DURATION_SEC = 10.0
DEFAULT_REMOTE_TIME_SLICES = 60
DEFAULT_REMOTE_COMMAND_TIMEOUT_SEC = 10.0
DEFAULT_SSH_HOST = "121.48.163.223"
DEFAULT_SSH_PORT = 22
DEFAULT_SSH_USERNAME = "s223"
DEFAULT_SSH_PRIVATE_KEY = os.path.expanduser("~/.ssh/id_ed25519_satellite_simulation")
DEFAULT_REDIS_PASSWORD_FILE = os.path.expanduser("~/.config/satellite-simulation/redis_password")


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def redis_password_from_env_or_file() -> Optional[str]:
    password = os.getenv("SATNET_REDIS_PASSWORD") or os.getenv("REDIS_PASSWORD")
    if password:
        return password

    try:
        with open(DEFAULT_REDIS_PASSWORD_FILE, encoding="utf-8") as password_file:
            return password_file.read().strip() or None
    except OSError:
        return None


def redis_config_from_env() -> Dict[str, Any]:
    """
    Fixed Redis/SSH connection settings for this project.

    Redis is disabled by default. Enable it in the GUI, or set
    SATNET_REDIS_ENABLED=1 before launching.
    """
    return {
        "enabled": env_bool("SATNET_REDIS_ENABLED", False),
        "host": DEFAULT_REDIS_HOST,
        "port": DEFAULT_REDIS_PORT,
        "password": redis_password_from_env_or_file(),
        "db": DEFAULT_REDIS_DB,
        "key_prefix": DEFAULT_REDIS_KEY_PREFIX,
        "loss_enabled": DEFAULT_REDIS_LOSS_ENABLED,
        "loss_scale": DEFAULT_REDIS_LOSS_SCALE,
        "socket_timeout": DEFAULT_REDIS_SOCKET_TIMEOUT,
        "use_ssh": True,
        "ssh_host": DEFAULT_SSH_HOST,
        "ssh_port": DEFAULT_SSH_PORT,
        "ssh_username": DEFAULT_SSH_USERNAME,
        "ssh_password": None,
        "ssh_private_key": DEFAULT_SSH_PRIVATE_KEY,
        "ssh_private_key_passphrase": None,
    }
