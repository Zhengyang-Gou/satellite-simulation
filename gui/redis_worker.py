"""Redis query worker moved out of the GUI thread."""

from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, Signal, Slot

from core.redis_latency import RedisLatencyProvider
from .link_state import LinkRecord


class RedisQueryWorker(QObject):
    """Run Redis and SSH tunnel I/O away from the GUI thread."""

    result_ready = Signal(int, object)
    error = Signal(int, str)

    def __init__(self, redis_config: Dict[str, Any]):
        super().__init__()
        self.redis_config = redis_config
        self.provider: Optional[RedisLatencyProvider] = None

    def _provider(self) -> RedisLatencyProvider:
        if self.provider is None:
            self.provider = RedisLatencyProvider(**self.redis_config)
        return self.provider

    @Slot(int, object, object)
    def query(self, query_id: int, active_links: List[LinkRecord], satellites: List[Any]) -> None:
        try:
            delay_map = self._provider().get_latest_delay_many(active_links, satellites)
            self.result_ready.emit(query_id, delay_map)
        except Exception as exc:  # Redis/SSH errors should never block or crash the UI.
            self.error.emit(query_id, str(exc))

    @Slot()
    def close(self) -> None:
        if self.provider is not None:
            self.provider.close()
            self.provider = None
