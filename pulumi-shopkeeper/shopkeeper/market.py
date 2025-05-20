import inspect
from typing import Any, Dict, Optional, TypedDict

from pulumi import ComponentResource, Input, Output, ResourceOptions

from shopkeeper import backend_factory


class MarketArgs(TypedDict):
    """
    Arguments required to declare a new market.

    Attributes:
        description (Input[str]): Description of the market.
        backend_declaration (Optional[Input[Dict[str, Any]]]): An optional dictionary containing
            additional configuration or declaration details for the backend.
        tags (Optional[Input[Dict[str, str]]]): A dictionary of key-value pairs used to tag the market
            with metadata.
        extensions (Optional[Input[Dict[str, Dict[str, str]]]]): Optional dictionary for market extensions.
    """

    description: Input[str]
    backend_declaration: Optional[
        Input[Dict[str, Any]]
    ]  # complex types are not yet supported
    tags: Optional[Input[Dict[str, str]]]
    extensions: Optional[Input[Dict[str, Dict[str, str]]]]


class Market(ComponentResource):
    """
    Pulumi component resource declaring a market.
    """

    market_data: Output[Dict[str, Any]]

    def __init__(
        self,
        name: str,
        args: MarketArgs,
        opts: Optional[ResourceOptions] = None,
    ) -> None:
        super().__init__("pulumi-shopkeeper:index:Market", name, props={}, opts=opts)

        # check if args["backend_declaration"] is awaitable
        if inspect.isawaitable(args["backend_declaration"]):
            raise NotImplementedError(
                "Input dependencies not yet implemented. Throw something back at a developer."
            )

        Backend = backend_factory.get(
            args["backend_declaration"]["backend_type"]  # type:ignore
        )
        self.market_data = Backend.declare(
            name=name,
            **args,
        )
        self.register_outputs({"marketData": self.market_data})


class ProducerArgs(TypedDict):
    """
    Arguments required to declare a new producer.
    """

    description: Input[str]
    backend_configuration: Input[Dict[str, Any]]
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

        # check if args["backend_configuration"] is awaitable
        if inspect.isawaitable(args["backend_configuration"]):
            raise NotImplementedError("Input dependencies not yet implemented.")

        if "backend_type" not in args["backend_configuration"]:
            raise KeyError("backend_type is required in backend_configuration")

        # declare the backend
        backend = backend_factory.get(
            args["backend_configuration"]["backend_type"]  # type:ignore
        )(**args.get("backend_configuration"))  # type: ignore

        backend.declare_producer(name=name, opts=ResourceOptions(parent=self), **args)


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
