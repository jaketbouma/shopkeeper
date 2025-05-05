import os
from abc import ABC, abstractmethod
from typing import Any, Dict

import pulumi

os.environ["AWS_PROFILE"] = "platform"


class MarketBackend(ABC):
    market_metadata: Dict[str, Any]

    def __init__(self, **kwargs):
        pass

    @abstractmethod
    @classmethod
    def declare(cls, **kwargs) -> pulumi.Output:
        pass

    @abstractmethod
    def declare_producer(self, **kwargs) -> pulumi.Output:
        pass


class MarketBackendFactory:
    def __init__(self):
        self._backends = {}

    def get(self, backend) -> MarketBackend:
        return self._backends[backend]

    def register(self, market_backend_name: str, market_backend_class: MarketBackend):
        self._backends[market_backend_name] = market_backend_class


factory = MarketBackendFactory()
