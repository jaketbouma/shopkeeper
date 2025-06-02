from typing import Optional, Type

from pulumi import ResourceOptions

from shopkeeper.market import ComponentResource


def ComponentClassFactory(
    component_name: str,
    Args,
) -> Type[ComponentResource]:
    """
    Abandoned -- dynamic types with Pulumi is asking for trouble.
    """
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

        self.marketData = {"mango": "orangish"}
        # do something
        self.register_outputs({"marketData": marketData})

    T = type(
        component_name,
        (ComponentResource,),
        {"__init__": _constructor, "marketData": marketData},
    )
    return T
