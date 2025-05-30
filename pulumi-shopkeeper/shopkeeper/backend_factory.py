from dataclasses import dataclass
from typing import Type

from pulumi import ComponentResource

from shopkeeper.aws.market import (
    AWSBackendConfiguration,
    AWSBackendDeclaration,
    AWSMarketBackend,
)
from shopkeeper.backend_interface import (
    MarketBackend,
    MarketBackendConfiguration,
    MarketBackendDeclaration,
)

# REGISTER A BACKEND HERE UNDER _market_backends
# manually, so that we can serve different versions easily in the future.
# Can look to streamline this registration later if we want to constrain
# versioning.
# 👇 👇 👇


@dataclass
class BackendSpec:
    name: str  # must be a valid Python identifier
    market_backend: Type[MarketBackend]
    market_backend_declaration: Type[MarketBackendDeclaration]
    market_backend_configuration: Type[MarketBackendConfiguration]

    def __post_init__(self):
        if not self.name.isidentifier():
            raise ValueError(f"{self.name!r} is not a valid Python identifier")


_market_backends: list[BackendSpec] = [
    BackendSpec(
        name="AwsV1",
        market_backend=AWSMarketBackend,
        market_backend_declaration=AWSBackendDeclaration,
        market_backend_configuration=AWSBackendConfiguration,
    ),
    BackendSpec(
        name="AwsLatest",
        market_backend=AWSMarketBackend,
        market_backend_declaration=AWSBackendDeclaration,
        market_backend_configuration=AWSBackendConfiguration,
    ),
]
# 👆 👆 👆
# REGISTER A BACKEND HERE UNDER _market_backends

_market_backend_dict = {b.name: b for b in _market_backends}


def get_backends() -> list[BackendSpec]:
    return _market_backends


def list_backends() -> list[BackendSpec]:
    return _market_backends


def get_market_backend(backend_name) -> Type[MarketBackend]:
    if backend_name not in _market_backend_dict:
        raise KeyError("Unknown Backend")
    return _market_backend_dict[backend_name].market_backend


def get_components() -> list[Type[ComponentResource]]:
    from shopkeeper.generated.components import components

    return components


def get_market_backend_component(backend_name):
    _market_backend_components_dict: dict[str, Type] = {
        c.__name__: c for c in get_components()
    }
    return _market_backend_components_dict[backend_name]
