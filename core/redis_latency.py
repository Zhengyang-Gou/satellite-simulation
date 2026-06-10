from typing import Any, Callable, Dict, List, Optional, Tuple

import redis

try:
    from sshtunnel import SSHTunnelForwarder
except Exception:  # sshtunnel is optional until SSH mode is enabled.
    SSHTunnelForwarder = None


class RedisLatencyProvider:
    """Read link metrics directly from Redis."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 6379,
        password: Optional[str] = None,
        db: int = 0,
        key_prefix: str = "link",
        loss_scale: float = 1.0,
        loss_enabled: bool = False,
        socket_timeout: float = 0.05,
        enabled: bool = True,
        use_ssh: bool = False,
        ssh_host: Optional[str] = None,
        ssh_port: int = 22,
        ssh_username: Optional[str] = None,
        ssh_password: Optional[str] = None,
        ssh_private_key: Optional[str] = None,
        ssh_private_key_passphrase: Optional[str] = None,
    ):
        self.enabled = enabled
        self.host = host
        self.port = int(port)
        self.password = password or None
        self.db = int(db)
        self.key_prefix = key_prefix or "link"
        self.loss_scale = float(loss_scale)
        self.loss_enabled = bool(loss_enabled)
        self.socket_timeout = float(socket_timeout)

        self.use_ssh = bool(use_ssh)
        self.ssh_host = ssh_host or ""
        self.ssh_port = int(ssh_port)
        self.ssh_username = ssh_username or ""
        self.ssh_password = ssh_password or None
        self.ssh_private_key = ssh_private_key or None
        self.ssh_private_key_passphrase = ssh_private_key_passphrase or None

        self.tunnel = None
        self.client: Optional[redis.Redis] = None

        self._connect()

    def _connect(self) -> None:
        connect_host = self.host
        connect_port = self.port

        if self.use_ssh:
            connect_host, connect_port = self._open_ssh_tunnel()

        self.client = redis.Redis(
            host=connect_host,
            port=connect_port,
            db=self.db,
            password=self.password,
            decode_responses=True,
            socket_timeout=self.socket_timeout,
            socket_connect_timeout=self.socket_timeout,
        )
        self.client.ping()

    def _open_ssh_tunnel(self) -> Tuple[str, int]:
        if SSHTunnelForwarder is None:
            raise RuntimeError("SSH 模式需要安装 'sshtunnel' 包，可执行：pip install sshtunnel")

        if not self.ssh_host:
            raise RuntimeError("启用 SSH 隧道时必须填写 SSH 主机")

        if not self.ssh_username:
            raise RuntimeError("启用 SSH 隧道时必须填写 SSH 用户名")

        ssh_kwargs: Dict[str, Any] = {
            "ssh_username": self.ssh_username,
            "remote_bind_address": (self.host, self.port),
            "local_bind_address": ("127.0.0.1", 0),
            "set_keepalive": 5.0,
        }

        if self.ssh_password:
            ssh_kwargs["ssh_password"] = self.ssh_password

        if self.ssh_private_key:
            ssh_kwargs["ssh_pkey"] = self.ssh_private_key

        if self.ssh_private_key_passphrase:
            ssh_kwargs["ssh_private_key_password"] = self.ssh_private_key_passphrase

        self.tunnel = SSHTunnelForwarder((self.ssh_host, self.ssh_port), **ssh_kwargs)
        self.tunnel.start()

        return "127.0.0.1", int(self.tunnel.local_bind_port)

    def close(self) -> None:
        if self.client is not None:
            try:
                self.client.close()
            except Exception:
                pass
            self.client = None

        if self.tunnel is not None:
            try:
                self.tunnel.stop()
            except Exception:
                pass
            self.tunnel = None

    def test_connection(self) -> Tuple[bool, str]:
        try:
            if self.client is None:
                self._connect()
            self.client.ping()
            if self.use_ssh:
                return True, f"SSH 隧道正常，Redis 正常：{self.ssh_host}:{self.ssh_port} -> {self.host}:{self.port}"
            return True, f"Redis 正常：{self.host}:{self.port}"
        except Exception as exc:
            return False, str(exc)

    def get_redis_sat_id(self, sat):
        if getattr(sat, "is_walker", False):
            return 10000 + (sat.plane_idx + 1) * 100 + (sat.node_idx + 1)

        return sat.sat_id

    def _metric_keys(self, src_id, tgt_id, metric):
        return [
            f"{self.key_prefix}:{src_id}:{tgt_id}:{metric}",
            f"{self.key_prefix}:{tgt_id}:{src_id}:{metric}",
        ]

    def _parse_metric_value(self, raw):
        if not raw:
            return "down"

        try:
            return round(float(str(raw).split(",")[-1]), 4)
        except Exception:
            return "down"

    def _parse_loss_pct(self, raw):
        if not raw:
            return "down"

        try:
            value = float(str(raw).split(",")[-1])
            return round((value / self.loss_scale) * 100.0, 4)
        except Exception:
            return "down"

    def _get_latest_many(
        self,
        links: List[Dict[str, Any]],
        satellites: List[Any],
        metric: str,
        parser: Callable[[Any], Any],
    ):
        result = {}

        if not links or not satellites:
            return result

        if self.client is None:
            self._connect()

        sat_ids = [self.get_redis_sat_id(sat) for sat in satellites]
        pipe = self.client.pipeline(transaction=False)
        query_plan = []

        for link in links:
            src_idx = link["src"]
            tgt_idx = link["tgt"]
            src_id = sat_ids[src_idx]
            tgt_id = sat_ids[tgt_idx]
            keys = self._metric_keys(src_id, tgt_id, metric)

            pipe.lrange(keys[0], -1, -1)
            pipe.lrange(keys[1], -1, -1)
            query_plan.append((src_idx, tgt_idx))

        try:
            redis_results = pipe.execute()
        except Exception:
            for link in links:
                result[(link["src"], link["tgt"])] = "down"
            return result

        pos = 0
        for src_idx, tgt_idx in query_plan:
            forward_result = redis_results[pos]
            reverse_result = redis_results[pos + 1]
            pos += 2

            latest = "down"
            if forward_result:
                latest = parser(forward_result[-1])
            elif reverse_result:
                latest = parser(reverse_result[-1])

            result[(src_idx, tgt_idx)] = latest

        return result

    def get_latest_metric_many(self, links: List[Dict[str, Any]], satellites: List[Any], metric: str):
        return self._get_latest_many(links, satellites, metric, self._parse_metric_value)

    def get_latest_loss_many(self, links: List[Dict[str, Any]], satellites: List[Any]):
        return self._get_latest_many(links, satellites, "loss", self._parse_loss_pct)

    def get_latest_link_metrics_many(self, links: List[Dict[str, Any]], satellites: List[Any]):
        metrics = {
            "cal": self.get_latest_metric_many(links, satellites, "cal"),
        }
        if self.loss_enabled:
            metrics["loss"] = self.get_latest_loss_many(links, satellites)
        return metrics
