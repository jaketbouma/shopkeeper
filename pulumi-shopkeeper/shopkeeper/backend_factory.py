from shopkeeper.aws_market import AWSMarketBackend  # noqa F401
from shopkeeper.backend_interface import MarketBackend  # noqa F401
from typing import Type


MARKET_BACKENDS = {"aws:v1": AWSMarketBackend, "aws:latest": AWSMarketBackend}


def get(backend_type) -> Type[MarketBackend]:
    if backend_type not in MARKET_BACKENDS:
        raise KeyError("Unknown Backend")
    return MARKET_BACKENDS[backend_type]
