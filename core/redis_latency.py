from typing import Any, Dict, List, Optional, Tuple

import redis

try:
    from sshtunnel import SSHTunnelForwarder
except Exception:  # sshtunnel is optional until SSH mode is enabled.
    SSHTunnelForwarder = None


class RedisLatencyProvider:
    """
    读取 Redis 中的链路 delay 数据。

    Redis key 格式：
        link:<src_id>:<tgt_id>:delay

    Redis value 格式：
        "timestamp,value"

    例如：
        "1777276267.242532,4155.000000"

    支持两种连接方式：
        1. 直连 Redis
        2. SSH tunnel 后连接远端 Redis

    SSH 模式下，host/port 表示远端服务器视角下的 Redis 地址端口。
    例如 Redis 只监听服务器本机 127.0.0.1:6379，则配置：
        use_ssh=True
        host="127.0.0.1"
        port=6379
        ssh_host="your.server.com"
        ssh_username="your_user"
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 6379,
        password: Optional[str] = None,
        db: int = 0,
        key_prefix: str = "link",
        delay_scale: float = 1000.0,
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
        """
        delay_scale:
            如果 Redis delay 单位是 us，转 ms 时用 1000.0。
            如果 Redis delay 本来就是 ms，用 1.0。
        """
        self.enabled = enabled
        self.host = host
        self.port = int(port)
        self.password = password or None
        self.db = int(db)
        self.key_prefix = key_prefix or "link"
        self.delay_scale = float(delay_scale)
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

        # Fail fast. Otherwise the first simulation query would be the first place
        # where a bad password / bad tunnel / wrong port becomes visible.
        self.client.ping()

    def _open_ssh_tunnel(self) -> Tuple[str, int]:
        if SSHTunnelForwarder is None:
            raise RuntimeError("SSH mode requires package 'sshtunnel'. Install it with: pip install sshtunnel")

        if not self.ssh_host:
            raise RuntimeError("SSH host is required when SSH tunnel is enabled")

        if not self.ssh_username:
            raise RuntimeError("SSH username is required when SSH tunnel is enabled")

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
                return True, f"SSH tunnel OK, Redis OK: {self.ssh_host}:{self.ssh_port} -> {self.host}:{self.port}"
            return True, f"Redis OK: {self.host}:{self.port}"
        except Exception as exc:
            return False, str(exc)

    def get_redis_sat_id(self, sat):
        """
        Walker 模式：
            Redis ID = 10000 + (plane_idx + 1) * 100 + (node_idx + 1)
            例如 plane_idx=2, node_idx=7 -> 10308

        TLE 模式：
            直接使用 TLE 的 sat_id
        """
        if getattr(sat, "is_walker", False):
            return 10000 + (sat.plane_idx + 1) * 100 + (sat.node_idx + 1)

        return sat.sat_id

    def _delay_keys(self, src_id, tgt_id):
        """
        Redis 里方向不一定双向都有。
        所以同时尝试 A:B 和 B:A。
        """
        return [
            f"{self.key_prefix}:{src_id}:{tgt_id}:delay",
            f"{self.key_prefix}:{tgt_id}:{src_id}:delay",
        ]

    def _parse_delay(self, raw):
        """
        raw 示例：
            "1777276267.242532,4155.000000"

        取逗号后面的 4155.000000。
        如果 delay_scale=1000，则显示为 4.155 ms。
        """
        if not raw:
            return "down"

        try:
            value = float(str(raw).split(",")[-1])
            return round(value / self.delay_scale, 4)
        except Exception:
            return "down"

    def get_latest_delay_many(self, links: List[Dict[str, Any]], satellites: List[Any]):
        """
        批量读取多条链路的最新 Redis delay。

        links:
            link_registry.values() 中的链路字典

        satellites:
            self.calculator.satellites

        返回：
            {
                (src_idx, tgt_idx): delay_ms 或 "down"
            }
        """
        result = {}

        if not links or not satellites:
            return result

        if self.client is None:
            self._connect()

        pipe = self.client.pipeline(transaction=False)
        query_plan = []

        for d in links:
            src_idx = d["src"]
            tgt_idx = d["tgt"]

            src_sat = satellites[src_idx]
            tgt_sat = satellites[tgt_idx]

            src_id = self.get_redis_sat_id(src_sat)
            tgt_id = self.get_redis_sat_id(tgt_sat)

            keys = self._delay_keys(src_id, tgt_id)

            # 每条链路查两个方向。
            pipe.lrange(keys[0], -1, -1)
            pipe.lrange(keys[1], -1, -1)

            query_plan.append((src_idx, tgt_idx, keys))

        try:
            redis_results = pipe.execute()
        except Exception:
            for d in links:
                result[(d["src"], d["tgt"])] = "down"
            return result

        pos = 0
        for src_idx, tgt_idx, _keys in query_plan:
            forward_result = redis_results[pos]
            reverse_result = redis_results[pos + 1]
            pos += 2

            latest = "down"

            if forward_result:
                latest = self._parse_delay(forward_result[-1])
            elif reverse_result:
                latest = self._parse_delay(reverse_result[-1])

            result[(src_idx, tgt_idx)] = latest

        return result
