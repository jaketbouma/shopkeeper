from typing import Any, Optional

from pulumi import Output, ResourceOptions
from pulumi.provider.experimental import component_provider_host

from shopkeeper.aws_market import (
    AWSBackendDeclaration,
    AWSMarketData,
)
from shopkeeper.market import ComponentResource


def ComponentClassFactory(
    component_name: str,
    Args,
    Return,
) -> ComponentResource:
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


components = [
    ComponentClassFactory(
        component_name="AWSMarket", Args=AWSBackendDeclaration, Return=AWSMarketData
    ),
    ComponentClassFactory(
        component_name="AnotherAWSMarket",
        Args=AWSBackendDeclaration,
        Return=AWSMarketData,
    ),
]

if __name__ == "__main__":
    component_provider_host(
        name="pulumi-shopkeeper",
        components=components,
    )
