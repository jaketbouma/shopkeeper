import logging
from abc import ABC
from typing import Any, Optional, Type, TypedDict

from pulumi import ComponentResource, Input, Output, ResourceOptions

logger = logging.getLogger(__name__)


class MarketMetadataV1(TypedDict):
    """
    Standard metadata common to all implementations of a market.
    """

    description: Input[str]
    color: Optional[Input[str]]
    environment: Optional[Input[str]]


class MarketClient(ABC):
    """
    A market client is used by data platform resources to interact with a market.
    """

    market_name: Optional[str] = None
    market_metadata_version: str = "v1"

    def __init__(self, **kwargs):
        pass

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


class Market(ComponentResource, ABC):
    """
    A market provides storage and organization of metadata of all
    other data platform resources.

    Producers and Consumers use a MarketClient to interact with the market.
    """

    market_data: Output[dict[str, str]]
    market_configuration: Output[dict[str, str]]
    metadata_version: str = "v1"
    safe_args: Any

    def __init__(
        self,
        name: str,
        args: Any,
        opts: Optional[ResourceOptions] = None,
    ) -> None:
        # if args is a dict coming from pulumi yaml, then deserialize
        self.args_type = self.__class__.__init__.__annotations__["args"]

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

    @classmethod
    def get_market_metadata_key(cls, name):
        """
        Returns the key (path in file-based backend) to a market's metadata file as a string
        """
        return f"/shopkeeper/market={name}/metadata-{cls.metadata_version}.json"


class MarketFactory:
    """
    A market factory provides flexible construction of markets and market clients.
    """

    _clients: dict[str, type[MarketClient]]
    _components: dict[str, type[Market]]
    _configurations: dict[str, Any]

    def __init__(self):
        self._clients = {}
        self._components = {}
        self._configurations = {}

    def register(
        self,
        market: Type["Market"],
        client: Type[MarketClient],
        configuration: Type[Any],
    ):
        market_type = market.__name__
        self._components[market_type] = market
        self._clients[market_type] = client
        self._configurations[market_type] = configuration

    def get_component(self, market_type: str):
        return self._components[market_type]

    def get_client(self, market_type: str):
        return self._clients[market_type]

    def get_configuration(self, market_type: str):
        return self._configurations[market_type]

    def configure_client(self, market_type, market_configuration) -> MarketClient:
        MC = self._clients[market_type]
        mc = MC(market_configuration=market_configuration)
        return mc
