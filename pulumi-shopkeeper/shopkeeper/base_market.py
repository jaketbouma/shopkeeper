import logging
from dataclasses import dataclass
from typing import Any, Optional, Type, TypeVar

from pulumi import ComponentResource, Output, ResourceOptions
from serde import from_dict

logger = logging.getLogger(__name__)


MarketConfigurationType = TypeVar(
    "MarketConfigurationType", bound="MarketConfiguration"
)


@dataclass
class MarketConfiguration:
    market_type: str
    # although subclasses contain this information,
    # market type is required explicitly here to support
    # the Pulumi Yaml interface, which has no knowledge of the subclasses.

    # ...subclasses can extend...


class MarketClient:
    market_name: Optional[str] = None
    market_configuration: MarketConfiguration
    market_metadata_version: str = "v1"

    def __init__(self, market_configuration: MarketConfiguration):
        self.market_configuration = market_configuration
        self.market_type = market_configuration.market_type

    def get_producer_metadata_key(self, producer_name):
        """
        Returns the key (path in file-based backend) to a producer metadata file as a string
        """
        return f"/shopkeeper/market={self.market_name}/producer={producer_name}/metadata-{self.market_metadata_version}.json"

    def get_dataset_metadata_key(self, producer_name, dataset_name):
        """
        Returns the key (path in file-based backend) to a dataset metadata file as a string
        """
        return f"/shopkeeper/market={self.market_name}/producer={producer_name}/dataset={dataset_name}/metadata-{self.market_metadata_version}.json"

    def get_market_metadata_key(self):
        return Market.get_market_metadata_key(self.market_name)


@dataclass
class MarketArgs:
    name: str
    description: str
    # market_version: is the resource type t


@dataclass
class MarketData:
    market_name: str
    market_type: str


class Market(ComponentResource):
    """
    The Metadata structure;

        market={market-name}/
        ├── metadata.json
        ├── [static html ux]
        ├── producer={producer-name}/
        │   ├── metadata.json
        │   └── dataset={dataset-name}/
        │       └── metadata.json
        └── consumer={consumer-name}/
            ├── metadata.json
            └── [infra declarations, approvals and other documentation]
    """

    market_data: Output[str]
    metadata_version: str = "v1"
    safe_args: Any

    def __init__(
        self,
        name: str,
        args: MarketArgs,
        opts: Optional[ResourceOptions] = None,
    ) -> None:
        # if args is a dict coming from pulumi yaml, then deserialize
        args_type = self.__class__.__init__.__annotations__["args"]
        if isinstance(args, dict):
            self.safe_args = from_dict(args_type, args)
        elif isinstance(args, args_type):
            self.safe_args = args

        # the name of the component we're registering
        typ = self.__class__.__name__
        t = f"pulumi-shopkeeper:index:{typ}"

        logger.info(f"Registering type '{typ}' at {t}")
        super().__init__(
            t,
            name,
            props={},
            opts=opts,
        )
        # self.client = client_factory.get(args.market_type)

    @classmethod
    def get_market_metadata_key(cls, name):
        """
        Returns the key (path in file-based backend) to a market's metadata file as a string
        """
        return f"/shopkeeper/market={name}/metadata-{cls.metadata_version}.json"


class MarketFactory:
    _clients: dict[str, type[MarketClient]]
    _components: dict[str, type["Market"]]

    def __init__(
        self,
        markets: Optional[dict[str, type["Market"]]] = None,
        clients: Optional[dict[str, type[MarketClient]]] = None,
    ):
        self._clients = clients or {}
        self._components = markets or {}

    def register(self, market: Type["Market"], client: Type[MarketClient]):
        market_type = market.__name__
        self._components[market_type] = market
        self._clients[market_type] = client

    def get_component(self, market_type: str):
        return self._clients[market_type]

    def get_client(self, market_type: str):
        return self._clients[market_type]

    def configure_client(
        self, market_configuration: MarketConfiguration
    ) -> MarketClient:
        MC = self._clients[market_configuration.market_type]
        mc = MC(market_configuration)
        return mc
