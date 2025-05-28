from typing import Any, Optional, Type

from pulumi import Output, ResourceOptions
from pulumi.provider.experimental import component_provider_host

from shopkeeper.aws_market import (
    AWSBackendDeclaration,
)
from shopkeeper.market import ComponentResource


def ComponentClassFactory(
    component_name: str,
    Args,
) -> Type[ComponentResource]:
    class GeneratedComponent(ComponentResource):
        market_data: Output[Any]

        def __init__(
            self,
            name: str,
            args: Args,  # type: ignore
            opts: Optional[ResourceOptions] = None,
        ):
            super().__init__(
                f"pulumi-shopkeeper:index:{component_name}", name, props={}, opts=opts
            )
            self.market_data = {"berry": "blue"}
            self.register_outputs({"marketData": self.market_data})

    GeneratedComponent.__name__ = component_name
    return GeneratedComponent


def ComponentClassFactory2(
    component_name: str,
    Args,
) -> Type[ComponentResource]:
    marketData: dict[str, str] = {"banana": "yellow"}

    def _constructor(
        self,
        name: str,
        args: Args,  # type: ignore
        opts: Optional[ResourceOptions] = None,
    ):
        ComponentResource.__init__(
            self, f"pulumi-shopkeeper:index:{component_name}", name, props={}, opts=opts
        )

        marketData = {"mango": "orangish"}
        # do something
        self.register_outputs({"marketData": marketData})

    T = type(
        component_name,
        (ComponentResource,),
        {"__init__": _constructor, "marketData": marketData},
    )
    return T


if __name__ == "__main__":
    components = [
        ComponentClassFactory2(component_name="AWSMarket", Args=AWSBackendDeclaration),
        ComponentClassFactory2(
            component_name="AWSMarket2",
            Args=AWSBackendDeclaration,
        ),
    ]
    component_provider_host(
        name="pulumi-shopkeeper",
        components=components,
    )
