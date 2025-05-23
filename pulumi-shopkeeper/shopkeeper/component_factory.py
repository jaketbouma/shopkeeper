from typing import Any, Optional

from pulumi import Output, ResourceOptions

from shopkeeper.aws_market import (  # noqa F401
    MarketBackendConfiguration,
    MarketBackendDeclaration,
)
from shopkeeper.market import ComponentResource


def ComponentClassFactory(
    component_name: str,
    Args,
    Return,
):
    class GeneratedComponent(ComponentResource):
        market_data: Output[Any]

        def __init__(
            self,
            name: str,
            args: Args,  # type: ignore
            opts: Optional[ResourceOptions] = None,
        ) -> Return:  # type: ignore
            super().__init__(
                f"pulumi-shopkeeper:index:{component_name}", name, props={}, opts=opts
            )
            self.register_outputs({})

    GeneratedComponent.__name__ = component_name
    return GeneratedComponent
