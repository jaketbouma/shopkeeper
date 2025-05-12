import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, TypedDict

from pulumi import ComponentResource, Input, Output, ResourceOptions

# Laziness, for now.
os.environ["AWS_PROFILE"] = "platform"


class MarketBackend(ABC):
    """
    A market backend stores and serves the metadata that defines data platform resources (data producers, consumers and datasets).

    This backend can be deployed on: AWS S3, Azure Storage, local filesystem and more.
    This abstract base class defines the common interface to these different underlying backends.
    """
  
    metadata_version: str = "v1"
    backend: str
    backend_configuration: Dict[str, Any]

    @abstractmethod
    def __init__(self, name: str, backend: str, backend_configuration: Dict[str, Any], tags=None):
        self.name = name
        self.backend = backend
        self.backend_configuration = backend_configuration
        self.tags = tags

    @classmethod
    @abstractmethod
    def declare(cls, name, **kwargs) -> "MarketBackend":
        pass

    @abstractmethod
    def declare_producer(self, *args, **kwargs) -> None:
        pass

    @abstractmethod
    def declare_dataset(self, *args, **kwargs) -> None:
        pass


class MarketBackendFactory:
    """
    A factory class for creating market backends.
    Backends have a unique name (`backend`) under which they are registered with the `register` method.
    """

    def __init__(self):
        self._backends = {}

    def get(self, backend) -> Type[MarketBackend]:
        return self._backends[backend]

    def register(self, market_backend_name: str, market_backend_class: Type[MarketBackend]):
        self._backends[market_backend_name] = market_backend_class


backend_factory = MarketBackendFactory()


class MarketArgs(TypedDict):
    """
    Arguments required to declare a new market.

    Attributes:
        description (Input[str]): ...
        backend (Input[str]): The type of backend for persisting and accessing metadata.
        backend_declaration (Optional[Input[Dict[str, Any]]]): An optional dictionary containing
            additional configuration or declaration details for the backend.
        tags (Input[Dict[str, str]]): A dictionary of key-value pairs used to tag the market
            with metadata.
    """

    description: Input[str]
    backend: Input[str]
    backend_declaration: Optional[Input[Dict[str, Any]]]
    tags: Input[Dict[str, str]]


class Market(ComponentResource):
    """
    Pulumi component resource declaring a market.
    """

    metadata: Output[Dict[str, Any]]
    backend: Output[str]
    backend_configuration: Output[Dict[str, Any]]

    def __init__(
        self,
        name: str,
        args: MarketArgs,
        opts: Optional[ResourceOptions] = None,
    ) -> None:
        super().__init__("pulumi-shopkeeper:index:Market", name, args, opts)
        self.billboard = f"Jake's Fine {args.get('description')} Store"

        Backend = backend_factory.get(backend=args.get("backend"))

        backend = args.get("backend")
        backend_declaration = args.get("backend_declaration")
        description = args.get("description")

        self.metadata = Output.from_input(
            {
                "description": description,
                "backend": backend,
                "_backend_declaration": backend_declaration,
            }
        )

        declaration_outputs = Backend.declare(
            metadata=self.metadata,
            tags=args.get("tags"),
            **backend_declaration,  # type:ignore
        )

        self.backend_configuration = declaration_outputs["backend_configuration"]

        self.register_outputs(
            {
                "backend_configuration": self.backend_configuration,
                "metadata": self.metadata,
            }
        )


class ProducerArgs(TypedDict):
    """
    Arguments required to declare a new producer.
    """

    backend: Input[str]
    backend_configuration: Input[Dict[str, Any]]
    metadata: Input[Dict[str, Any]]
    tags: Input[Dict[str, str]]


class Producer(ComponentResource):
    """
    Pulumi component resource declaring a producer.
    """

    def __init__(
        self,
        name: str,
        args: ProducerArgs,
        opts: Optional[ResourceOptions] = None,
    ) -> None:
        super().__init__("pulumi-shopkeeper:index:Producer", name, args, opts)

        backend = backend_factory.get(backend=args.get("backend"))(
            tags=args.get("tags"),
            **args.get("backend_configuration"),  # type:ignore
        )
        p = backend.declare_producer(
            name=name, metadata=args.get("metadata"), opts=ResourceOptions(parent=self)
        )
        print(p)


class DatasetArgs(TypedDict):
    """
    Arguments required to declare a new dataset.
    """

    backend: Input[str]
    backend_configuration: Input[Dict[str, Any]]
    producer_name: Input[str]
    metadata: Input[Dict[str, Any]]
    configuration: Input[Dict[str, Any]]
    tags: Input[Dict[str, str]]


class Dataset(ComponentResource):
    """
    Pulumi component resource declaring a dataset.
    """

    def __init__(
        self,
        name: str,
        args: DatasetArgs,
        opts: Optional[ResourceOptions] = None,
    ) -> None:
        super().__init__("pulumi-shopkeeper:index:Dataset", name, args, opts)

        backend = backend_factory.get(backend=args.get("backend"))(
            tags=args.get("tags"),
            **args.get("backend_configuration"),  # type:ignore
        )
        d = backend.declare_dataset(
            name=name,
            metadata=args.get("metadata"),
            configuration=args.get("configuration"),
            opts=ResourceOptions(parent=self),
        )
        print(d)
