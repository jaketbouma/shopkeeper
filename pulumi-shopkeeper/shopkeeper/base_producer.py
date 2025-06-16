import logging
from typing import Any, Optional, TypedDict

from pulumi import ComponentResource, Input, Output, ResourceOptions

from shopkeeper.factory import market_factory

logger = logging.getLogger(__name__)


class ProducerMetadataV1(TypedDict):
    name: Input[str]
    description: Input[str]
    version: Optional[str]


class Producer(ComponentResource):
    producer_data: Output[Any]
    market_type: str

    def __init__(
        self,
        name: str,
        args: Any,
        opts: Optional[ResourceOptions] = None,
    ) -> None:
        super().__init__(
            f"pulumi-shopkeeper:index:{self.__class__.__name__}",
            name,
            props={},
            opts=opts,
        )

        # configure client
        self.market_client = market_factory.configure_client(
            market_type=self.market_type, market_configuration=args["market"]
        )
