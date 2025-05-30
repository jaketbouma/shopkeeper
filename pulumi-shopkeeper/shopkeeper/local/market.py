import os
from dataclasses import dataclass
from typing import Any, Optional, TypeVar

from pulumi import ComponentResource, Output, ResourceOptions
from serde import from_dict, serde
from serde.yaml import to_yaml


@dataclass
class MarketConfiguration:
    market_type: str
    # ...subclasses can extend...


class MarketClient:
    market_type: str
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


class ClientFactory:
    _clients: dict[str, type[MarketClient]]

    def __init__(self, clients: Optional[dict[str, type[MarketClient]]] = None):
        self._clients = clients or {}

    def register(self, market_type: str, client_cls: type[MarketClient]):
        self._clients[market_type] = client_cls

    def get(self, market_configuration: MarketConfiguration) -> MarketClient:
        M = self._clients[market_configuration.market_type]
        m = M(market_configuration)
        return m


@dataclass
class MarketArgs:
    name: str
    description: str
    market_type: str


@dataclass
class MarketData:
    name: str
    version: str


class Market(ComponentResource):
    marketData: Output[str]
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

        super().__init__(
            f"pulumi-shopkeeper:index:{self.safe_args.market_type}",
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


@dataclass
class LocalMarketArgs(MarketArgs):
    path: str


@dataclass
class LocalMarketConfiguration(MarketConfiguration):
    metadata_file: str


@dataclass
@serde
class LocalMarketData(MarketData):
    path: str
    metadata_file: str


class LocalMarket(Market):
    marketData: Output[str]

    def __init__(self, name, args: LocalMarketArgs, opts):
        super().__init__(name, args, opts)

        filename = os.path.join(
            self.safe_args.path, Market.get_market_metadata_key(name=name)
        )
        market_data = LocalMarketData(
            name=name, version="v0", path=self.safe_args.path, metadata_file=filename
        )
        output_market_data = to_yaml(market_data)

        # pretend to create a file
        market_metadata_file = dict(
            name="market-metadata-file", content=output_market_data, filename=filename
        )

        self.marketData = Output.from_input(output_market_data)
        self.register_outputs({"marketData": output_market_data})


MarketConfigurationType = TypeVar(
    "MarketConfigurationType", bound="MarketConfiguration"
)


@dataclass
class ProducerArgs:
    market: Any
    name: str
    description: str


@dataclass
class ProducerData:
    market: Any
    name: str
    description: str
    metadata_file: str


class Producer(ComponentResource):
    producerData: Output[str]
    metadata_version: str = "v1"
    safe_args: Any
    client: MarketClient

    def __init__(
        self,
        name: str,
        args: ProducerArgs,
        opts: Optional[ResourceOptions] = None,
    ) -> None:
        # if args is a dict coming from pulumi yaml, then deserialize
        args_type = self.__class__.__init__.__annotations__["args"]
        if isinstance(args, dict):
            self.safe_args = from_dict(args_type, args)
        elif isinstance(args, args_type):
            self.safe_args = args

        super().__init__(
            f"pulumi-shopkeeper:index:{self.safe_args.market.market_type}Producer",
            name,
            props={},
            opts=opts,
        )
        self.client = client_factory.get(self.safe_args.market)


class LocalMarketClient(MarketClient):
    def __init__(self, market_configuration: LocalMarketConfiguration):
        super().__init__(market_configuration)
        self.market_name = "fixme"


@dataclass
class LocalProducerArgs(ProducerArgs):
    market: LocalMarketConfiguration
    color: Optional[str]


@dataclass
class LocalProducerData(ProducerData):
    color: Optional[str]
    metadata_file: str


class LocalProducer(Producer):
    producerData: Output[str]

    def __init__(
        self, name: str, args: LocalProducerArgs, opts: Optional[ResourceOptions] = None
    ):
        super().__init__(name, args, opts)

        filename = self.client.get_producer_metadata_key(self.safe_args.name)

        producer_data = LocalProducerData(
            market=self.safe_args.market,
            name=self.safe_args.name,
            description=self.safe_args.description,
            color=self.safe_args.color,
            metadata_file=filename,
        )
        output_producer_data = to_yaml(producer_data)

        # pretend to create a file
        producer_metadata_file = dict(
            name="producer-metadata-file",
            content=output_producer_data,
            filename=filename,
        )

        self.producerData = Output.from_input(output_producer_data)
        self.register_outputs({"producerData": output_producer_data})


client_factory = ClientFactory(clients={"LocalMarket": MarketClient})
