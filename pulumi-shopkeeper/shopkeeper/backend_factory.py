from shopkeeper.aws_market import AWSMarketBackend  # noqa F401
from shopkeeper.backend_interface import MarketBackend  # noqa F401
from typing import Type


MARKET_BACKENDS = {"aws:v1": AWSMarketBackend, "aws:latest": AWSMarketBackend}


def get(backend_type) -> Type[MarketBackend]:
    return MARKET_BACKENDS[backend_type]
