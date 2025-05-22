from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Optional

from pulumi import Output, ResourceOptions


@dataclass
class MarketBackendDeclaration:
    backend_type: str
    backend_opts: ResourceOptions


@dataclass
class MarketBackendConfiguration:
    backend_type: str
    # ...subclasses can extend...


@dataclass
class MarketData[T: MarketBackendConfiguration]:
    metadata_version: str
    name: str
    description: str
    backend_configuration: T
    backend_tags: Dict[str, str]
    # ...subclasses can extend...


class MarketBackend[
    MarketBackendConfigurationType: MarketBackendConfiguration,
    MarketBackendDeclarationType: MarketBackendDeclaration,
](ABC):
    """
    A market backend stores and serves the metadata that defines data platform
    resources (data producers, consumers and datasets).

    A MarketBackend can be deployed on: AWS S3, Azure Storage, local filesystem and more.
    This abstract base class defines the common interface to these different underlying backends.
    """

    metadata_version: str = "v1"
    _market_data: MarketData[MarketBackendConfigurationType]

    @abstractmethod
    def __init__(
        self,
        backend_configuration: MarketBackendConfigurationType,
        market_data: Optional[MarketData[MarketBackendConfigurationType]] = None,
    ):
        if market_data is None:
            raise NotImplementedError(
                "MarketBackend is an abstract class and its constructor should only be called from subclasses."
            )

        # The configuration of the client must match what is in the saved metadata
        if market_data.backend_configuration != backend_configuration:
            raise ValueError(
                "The backend configuration used to connect does not match saved market_data"
            )

        # Attributes we can expect across all subclasses
        self.name = market_data.name
        self.description = market_data.description
        self.backend_configuration = market_data.backend_configuration
        self.backend_tags = market_data.backend_tags
        self._market_data = market_data

    @classmethod
    def get_market_metadata_key(cls, name):
        """
        Returns the key (path in file-based backend) to a market's metadata file as a string
        """
        return f"/shopkeeper/market={name}/metadata-{cls.metadata_version}.json"

    def get_producer_metadata_key(self, producer_name):
        """
        Returns the key (path in file-based backend) to a producer metadata file as a string
        """
        return f"/shopkeeper/market={self.name}/producer={producer_name}/metadata-{self.metadata_version}.json"

    def get_dataset_metadata_key(self, producer_name, dataset_name):
        """
        Returns the key (path in file-based backend) to a dataset metadata file as a string
        """
        return f"/shopkeeper/market={self.name}/producer={producer_name}/dataset={dataset_name}/metadata-{self.metadata_version}.json"

    @classmethod
    @abstractmethod
    def declare_market(
        cls,
        name: str,
        backend_declaration: MarketBackendDeclarationType,
    ) -> Output[MarketData]:
        pass

    @abstractmethod
    def declare_producer(self, *args, **kwargs) -> Output[Dict]:
        pass

    @abstractmethod
    def declare_dataset(self, *args, **kwargs) -> Output[Dict]:
        pass
