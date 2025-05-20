import os
from abc import ABC, abstractmethod
from typing import Any, Dict

from pulumi import Output

# Laziness, for now.
os.environ["AWS_PROFILE"] = "platform"


class MarketBackend(ABC):
    """
    A market backend stores and serves the metadata that defines data platform
    resources (data producers, consumers and datasets).

    A MarketBackend can be deployed on: AWS S3, Azure Storage, local filesystem and more. This abstract base class defines the common interface to these different underlying backends.
    """

    metadata_version: str = "v1"
    backend_type: str
    backend_configuration: Dict[str, Any]

    @abstractmethod
    def __init__(
        self,
        name: str,
        backend_configuration: Dict[str, Any],
        tags=None,
    ):
        self.name = name
        self.backend_configuration = backend_configuration
        self.tags = tags

    @classmethod
    @abstractmethod
    def declare_market(cls, name, args, opts=None) -> Output[Dict]:
        pass

    @abstractmethod
    def declare_producer(self, *args, **kwargs) -> Output[Dict]:
        pass

    @abstractmethod
    def declare_dataset(self, *args, **kwargs) -> Output[Dict]:
        pass

    def get_producer_metadata_key(self, producer_name):
        """
        Returns the key (path in file-based backend) to a producer metadata file as a string
        """
        return f"/shopkeeper/market={self.name}/producer={producer_name}/metadata-{self.metadata_version}.json"

    @classmethod
    def get_market_metadata_key(cls, name):
        """
        Returns the key (path in file-based backend) to a market's metadata file as a string
        """
        return f"/shopkeeper/market={name}/metadata-{cls.metadata_version}.json"

    def get_dataset_metadata_key(self, producer_name, dataset_name):
        """
        Returns the key (path in file-based backend) to a dataset metadata file as a string
        """
        return f"/shopkeeper/market={self.name}/producer={producer_name}/dataset={dataset_name}/metadata-{self.metadata_version}.json"
