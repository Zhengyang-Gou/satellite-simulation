"""Runtime configuration helpers for the GUI layer."""

import os
from typing import Any, Dict, Optional


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def env_str_or_none(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    return value or None


def redis_config_from_env() -> Dict[str, Any]:
    """
    Redis connection settings.

    Redis is disabled by default. Enable it in the GUI, or set:
        SATNET_REDIS_ENABLED=1

    Direct Redis variables:
        SATNET_REDIS_HOST, SATNET_REDIS_PORT, SATNET_REDIS_DB,
        SATNET_REDIS_PASSWORD, SATNET_REDIS_KEY_PREFIX,
        SATNET_REDIS_DELAY_SCALE, SATNET_REDIS_SOCKET_TIMEOUT

    SSH tunnel variables:
        SATNET_REDIS_USE_SSH,
        SATNET_SSH_HOST, SATNET_SSH_PORT, SATNET_SSH_USERNAME,
        SATNET_SSH_PASSWORD, SATNET_SSH_PRIVATE_KEY,
        SATNET_SSH_PRIVATE_KEY_PASSPHRASE

    REDIS_PASSWORD is also accepted as a fallback for Redis password.
    """
    return {
        "enabled": env_bool("SATNET_REDIS_ENABLED", False),
        "host": os.getenv("SATNET_REDIS_HOST", "127.0.0.1"),
        "port": env_int("SATNET_REDIS_PORT", 6380),
        "password": os.getenv("SATNET_REDIS_PASSWORD") or os.getenv("REDIS_PASSWORD") or None,
        "db": env_int("SATNET_REDIS_DB", 0),
        "key_prefix": os.getenv("SATNET_REDIS_KEY_PREFIX", "link"),
        "delay_scale": env_float("SATNET_REDIS_DELAY_SCALE", 1000.0),
        "socket_timeout": env_float("SATNET_REDIS_SOCKET_TIMEOUT", 0.05),
        "use_ssh": env_bool("SATNET_REDIS_USE_SSH", False),
        "ssh_host": env_str_or_none("SATNET_SSH_HOST", ""),
        "ssh_port": env_int("SATNET_SSH_PORT", 22),
        "ssh_username": env_str_or_none("SATNET_SSH_USERNAME", ""),
        "ssh_password": env_str_or_none("SATNET_SSH_PASSWORD", None),
        "ssh_private_key": env_str_or_none("SATNET_SSH_PRIVATE_KEY", None),
        "ssh_private_key_passphrase": env_str_or_none("SATNET_SSH_PRIVATE_KEY_PASSPHRASE", None),
    }
