import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, TypedDict

from pulumi import ComponentResource, Input, Output, ResourceOptions

os.environ["AWS_PROFILE"] = "platform"


class MarketBackend(ABC):
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


class MarketBackendFactory:
    def __init__(self):
        self._backends = {}

    def get(self, backend) -> Type[MarketBackend]:
        return self._backends[backend]

    def register(self, market_backend_name: str, market_backend_class: Type[MarketBackend]):
        self._backends[market_backend_name] = market_backend_class


backend_factory = MarketBackendFactory()


class MarketArgs(TypedDict):
    speciality: Input[str]
    backend: Input[str]
    backend_declaration: Optional[Input[Dict[str, Any]]]
    tags: Input[Dict[str, str]]


class Market(ComponentResource):
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
        self.billboard = f"Jake's Fine {args.get('speciality')} Store"

        Backend = backend_factory.get(backend=args.get("backend"))

        backend = args.get("backend")
        backend_declaration = args.get("backend_declaration")
        speciality = args.get("speciality")

        self.metadata = {
            "speciality": speciality,
            "backend": backend,
            "_backend_declaration": backend_declaration,
        }

        declare_outputs = Backend.declare(
            metadata=self.metadata, tags=args.get("tags"), **backend_declaration
        )

        self.backend_configuration = declare_outputs["backend_configuration"]

        self.register_outputs(
            {
                "backend_configuration": self.backend_configuration,
                "metadata": self.metadata,
            }
        )


class ProducerArgs(TypedDict):
    backend: Input[str]
    backend_configuration: Input[Dict[str, Any]]
    metadata: Input[Dict[str, Any]]
    tags: Input[Dict[str, str]]


class Producer(ComponentResource):
    def __init__(
        self,
        name: str,
        args: ProducerArgs,
        opts: Optional[ResourceOptions] = None,
    ) -> None:
        super().__init__("pulumi-shopkeeper:index:Producer", name, args, opts)

        backend = backend_factory.get(backend=args.get("backend"))(
            tags=args.get("tags"), **args.get("backend_configuration")
        )
        p = backend.declare_producer(
            name=name, metadata=args.get("metadata"), opts=ResourceOptions(parent=self)
        )
        print(p)


class DatasetArgs(TypedDict):
    backend: Input["str"]
    backend_configuration: Input[Dict[str, Any]]
    producer_name: Input[str]
    metadata: Input[Dict[str, Any]]
    configuration: Input[Dict[str, Any]]
    tags: Input[Dict[str, str]]


class Dataset(ComponentResource):
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
