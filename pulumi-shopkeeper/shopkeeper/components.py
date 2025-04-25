from typing import Optional, TypedDict
import pulumi
from pulumi import Inputs, ResourceOptions
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MarketplaceArgs(TypedDict):
    address: pulumi.Input[str]
    speciality: pulumi.Input[str]


class Marketplace(pulumi.ComponentResource):
    billboard: pulumi.Output[str]
    address: pulumi.Output[str]

    def __init__(
        self, name: str, args: MarketplaceArgs, opts: Optional[ResourceOptions] = None
    ) -> None:

        super().__init__("pulumi-shopkeeper:index:Marketplace", name, args, opts)

        self.billboard = f"Jake's Fine {args.get("speciality")} Store"
        self.register_outputs({"billboard": self.billboard, "address": args.get("address")})


class ProducerArgs(TypedDict):
    marketplaceAddress: pulumi.Input[str]


class Producer(pulumi.ComponentResource):
    def __init__(
        self, name: str, args: ProducerArgs, opts: Optional[ResourceOptions] = None
    ) -> None:

        super().__init__("pulumi-shopkeeper:index:Producer", name, args, opts)
        self.register_outputs({})