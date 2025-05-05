import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, TypedDict

import pulumi
from pulumi import ResourceOptions

os.environ["AWS_PROFILE"] = "platform"


class MarketBackend(ABC):
    market_metadata: Dict[str, Any]

    def __init__(self, **kwargs):
        pass

    @classmethod
    @abstractmethod
    def declare(cls, **kwargs) -> pulumi.Output:
        pass

    @abstractmethod
    def declare_producer(self, **kwargs) -> pulumi.Output:
        pass


class MarketBackendFactory:
    def __init__(self):
        self._backends = {}

    def get(self, backend) -> MarketBackend:
        return self._backends[backend]

    def register(self, market_backend_name: str, market_backend_class: MarketBackend):
        self._backends[market_backend_name] = market_backend_class


backend_factory = MarketBackendFactory()


class MarketArgs(TypedDict):
    speciality: pulumi.Input[str]
    backend: pulumi.Input[str]
    backend_declaration: Optional[pulumi.Input[Dict[str, Any]]]


class Market(pulumi.ComponentResource):
    metadata: pulumi.Output[Dict[str, Any]]
    backend: pulumi.Output[str]
    backend_configuration: pulumi.Output[[str, Any]]

    def __init__(
        self,
        name: str,
        args: MarketArgs,
        opts: Optional[ResourceOptions] = None,
    ) -> None:
        super().__init__("pulumi-shopkeeper:index:Market", name, args, opts)
        self.billboard = f"Jake's Fine {args.get('speciality')} Store"

        Backend = backend_factory.get(backend=args.get("backend"))

        metadata = pulumi.Output.all(
            backend=args.get("backend"),
            backend_declaration=args.get("backend_declaration"),
            speciality=args.get("speciality"),
        )

        self.declare_outputs = Backend.declare(metadata=metadata, **args.get("backend_declaration"))

        self.backend_configuration = self.declare_outputs.backend_configuration
        self.backend = args.get("backend")

        self.register_outputs(
            {"backend_configuration": self.backend_configuration, "backend": self.backend}
        )


class ProducerArgs(TypedDict):
    backend: pulumi.Input[str]
    backend_configuration: pulumi.Input[str]


class Producer(pulumi.ComponentResource):
    def __init__(
        self,
        name: str,
        args: MarketArgs,
        opts: Optional[ResourceOptions] = None,
    ) -> None:
        super().__init__("pulumi-shopkeeper:index:Market", name, args, opts)
        Backend = backend_factory.get(backend=args.get("backend"))
        backend = Backend(**args.get("backend_configuration"))
        print(backend)
