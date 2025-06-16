import logging
from abc import ABC
from dataclasses import asdict, is_dataclass
from typing import Any, Optional, Type, TypedDict

import dacite

# can't use dacite either
# error: pulumi-shopkeeper:index:AwsProducerV1 resource 'dev' has a problem:
# Unexpected <class 'Exception'>: can not resolve forward reference: name 'T' is not defined:
import yaml
from pulumi import ComponentResource, Input, Output, ResourceOptions

logger = logging.getLogger(__name__)


class SerializationMixin:
    """
    Mixin provides functions to serde Pulumi Input and Output types in dataclasses.
    (Pyserde isn't happy about the ForwardRef[T] in Pulumi IO types)
    """

    def to_dict(self) -> dict[str, Any]:
        if is_dataclass(self):
            return asdict(self)
        else:
            raise (Exception("Serialization Mixin only supports dataclasses"))

    def to_yaml(self) -> str:
        return yaml.safe_dump(self.to_dict())

    @classmethod
    def from_yaml(cls, s: str):
        data = yaml.safe_load(s)
        return cls(**data)

    @classmethod
    def from_dict(cls, data: dict):
        logger.info(data)
        return dacite.from_dict(cls, data, dacite.Config(forward_references={"T": Any}))


class MarketMetadataV1(TypedDict):
    description: Optional[Input[str]]
    color: Optional[Input[str]]
    environment: Optional[Input[str]]


class MarketClient(ABC):
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
        # self.client = client_factory.get(args.market_type)

    @classmethod
    def get_market_metadata_key(cls, name):
        """
        Returns the key (path in file-based backend) to a market's metadata file as a string
        """
        return f"/shopkeeper/market={name}/metadata-{cls.metadata_version}.json"


class MarketFactory:
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

    def configure_client(self, market_configuration: Any) -> MarketClient:
        MC = self._clients[market_configuration.market_type]
        mc = MC(market_configuration)
        return mc
