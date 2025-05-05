import os
from typing import Any, Dict, Optional, TypedDict

import market_backend
import pulumi
from pulumi import ResourceOptions

os.environ["AWS_PROFILE"] = "platform"


class MarketArgs(TypedDict):
    speciality: pulumi.Input[str]
    backend: pulumi.Input[str]
    backend_declaration: Optional[pulumi.Input[Dict[str, Any]]]


class Market(pulumi.ComponentResource):
    metadata: pulumi.Output[Dict[str, Any]]

    def __init__(
        self,
        name: str,
        args: MarketArgs,
        opts: Optional[ResourceOptions] = None,
    ) -> None:
        super().__init__("pulumi-shopkeeper:index:Market", name, args, opts)
        self.billboard = f"Jake's Fine {args.get('speciality')} Store"

        Backend = market_backend.factory.from_backend_property(backend=args.get("backend"))

        metadata = pulumi.Output.all(
            backend=args.get("backend"),
            backend_configuration=args.get("backend_declaration"),
            speciality=args.get("speciality"),
        )

        backend = Backend.declare(metadata=metadata, **args.get("backend_declaration"))

        print(backend)


class ProducerArgs(TypedDict):
    backend: pulumi.Input(str)
    backend_configuration: pulumi.Input(str)


class Producer(pulumi.ComponentResource):
    def __init__(
        self,
        name: str,
        args: MarketArgs,
        opts: Optional[ResourceOptions] = None,
    ) -> None:
        super().__init__("pulumi-shopkeeper:index:Market", name, args, opts)
        Backend = market_backend.factory.from_backend_property(backend=args.get("backend"))
        backend = Backend(**args.get("backend_configuration"))
        print(backend)
