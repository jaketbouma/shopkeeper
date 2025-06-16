import logging
from dataclasses import dataclass
from typing import Any, Optional

from pulumi import ComponentResource, Input, Output, ResourceOptions

from shopkeeper.base_market import MarketClient, SerializationMixin
from shopkeeper.factory import market_factory

logger = logging.getLogger(__name__)


@dataclass
class ProducerMetadataV1(SerializationMixin):
    name: Input[str]
    description: Input[str]
    version: Optional[str] = "v1"


class Producer(ComponentResource):
    producer_data: Output[Any]
    metadata_version: str = "v1"
    safe_args: Any
    market_client: MarketClient

    def __init__(
        self,
        name: str,
        args: Any,
        opts: Optional[ResourceOptions] = None,
    ) -> None:
        # if args is a dict coming from pulumi yaml, then deserialize
        args_type = self.__class__.__init__.__annotations__["args"]
        if isinstance(args, dict):
            self.safe_args = args_type.from_dict(args)
        elif isinstance(args, args_type):
            self.safe_args = args

        super().__init__(
            f"pulumi-shopkeeper:index:{self.safe_args.market.market_type}Producer",
            name,
            props={},
            opts=opts,
        )

        # configure client
        self.market_client = market_factory.configure_client(
            market_configuration=self.safe_args.market
        )
