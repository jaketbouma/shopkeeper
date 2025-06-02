import inspect
from typing import Any, Dict, Optional, TypedDict

from pulumi import ComponentResource, Input, Output, ResourceOptions

from shopkeeper import backend_factory
from shopkeeper.backend_interface import (  # noqa F401
    MarketBackendDeclaration,
)


class MarketArgs(TypedDict):
    backend_declaration: str
    description: str
    tags: Dict[str, str] | None
    extensions: Dict[str, Dict[str, str]] | None


class Market[T: MarketBackendDeclaration](ComponentResource):
    """
    Pulumi component resource declaring a market.
    """

    market_data: Output[Any]

    def __init__(
        self,
        name: str,
        args: T,
        opts: Optional[ResourceOptions] = None,
    ) -> None:
        super().__init__(
            f"pulumi-shopkeeper:index:{args.backend_type}", name, props={}, opts=opts
        )

        # check if args["backend_declaration"] is awaitable
        if inspect.isawaitable(args):
            raise NotImplementedError(
                "Input dependencies not yet implemented. Throw something back at a developer."
            )

        Backend = backend_factory.get_market_backend(args.backend_type)
        self.market_data = Backend.declare_market(
            name=name,
            backend_declaration=args,
        )

        self.register_outputs({"marketData": self.market_data})


class ProducerArgs(TypedDict):
    """
    Arguments required to declare a new producer.
    """

    description: Input[str]
    backend_configuration: Input[Dict[str, Any]]
    tags: Optional[Input[Dict[str, str]]]
    extensions: Optional[Input[Dict[str, Dict[str, str]]]]


class Producer(ComponentResource):
    """
    Pulumi component resource declaring a producer.
    """

    market_data: Output[Dict[str, Any]]

    def __init__(
        self,
        name: str,
        args: ProducerArgs,
        opts: Optional[ResourceOptions] = None,
    ) -> None:
        super().__init__("pulumi-shopkeeper:index:Producer", name, args, opts)

        # check if args["backend_configuration"] is awaitable
        if inspect.isawaitable(args["backend_configuration"]):
            raise NotImplementedError("Input dependencies not yet implemented.")

        if "backend_type" not in args["backend_configuration"]:
            raise KeyError("backend_type is required in backend_configuration")

        # ensure that parent is passed through
        opts = ResourceOptions.merge(ResourceOptions(parent=self), opts)

        # initialize the backend
        Backend = backend_factory.get(
            args["backend_configuration"]["backend_type"]  # type:ignore
        )
        backend = Backend(backend_configuration=args.get("backend_configuration"))

        # declare the producer
        self.producer_data = backend.declare_producer(
            name=name,
            args=args,
            opts=opts,
        )

        # wrap up
        self.register_outputs({"producerData": self.producer_data})


class DatasetArgs(TypedDict):
    """
    Arguments required to declare a new dataset.
    """

    backend_type: Input[str]
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

        backend = backend_factory.get(backend_type=args.get("backend_type"))(
            backend_configuration=args.get("backend_configuration"),
        )
        d = backend.declare_dataset(
            name=name,
            metadata=args.get("metadata"),
            configuration=args.get("configuration"),
            opts=ResourceOptions(parent=self),
        )
        print(d)
