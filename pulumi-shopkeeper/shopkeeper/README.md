# Building data platform components across multiple platforms

## Markets

Language:
* "Market": A resource (combination of various infrastructure definitions) that encapsulates all other data platform resources, providing organization, metadata storage, and access policy source of truth.
* "Market client": A python class that is to interact with a market that has already been declared. Producer, consumer and dataset resources initialize a market client to declare their metadata.
* "Market configuration": The parameters needed to connect to a market, that are used to instantiate a market client.
* "Producer / Consumer / Dataset": Other data platform resources.

Markets are implemented across various cloud providers and PaaS. We try to separate what is the same across all platforms and refer to this as (market/producer/consumer) "metadata".

Markets are implemented at e.g. `some_market/market.py` by;
* Subclassing `base_market.Market`, an ABC which implements Pulumi component basics and standard market metadata file path creation. The name of this subclass is the `market_type`.
* Subclassing `base_market.MarketClient`, an ABC which implements standard producer, consumer and dataset metadata file path creation, and expected methods to read metadata stored in the market.
* Defining the market configuration that is needed to connect to the market as a `TypedDict`.

:warning: Note: Pulumi Component Resources are still experimental. Inputs and Outputs are particularly fragile across languages. Some strong recommendations are recommended below.

The default metadata structure for file based markets (AWS, Azure, GCP) is implemented by the abovementioned base classes as follows.
```text
    market={market-name}/
    ├── metadata-{metadata-version}.yaml
    ├── [static html ux]
    ├── producer={producer-name}/
    │   ├── metadata-{metadata-version}.yaml
    │   └── dataset={dataset-name}/
    │       └── metadata-{metadata-version}.json
    └── consumer={consumer-name}/
        ├── metadata-{metadata-version}.yaml
        └── [infra declarations, approvals and other documentation]
```

Markets are registered in a factory (`factory.market_factory.register(market:Market, client:MarketClient, configuration:TypedDict)`) so that they can be accessed by the market's class name (`market_type := market.__name__`).

## Data platform resources
Producers, Consumers and Datasets across various platforms are implemented in a similar way.

#### Define the inputs: `class ResourceVXArgs(TypedDict)`
The args (or `properties`) that declare the data platform resource. We aim for the standard form of;
- `metadata`: metadata that is common to all implementations of this resource. Must include a `metadata.metadata_version`.
- `market`: market configuration that defines how to connect to a market.
- `...`: the rest of the namespace can be used for data that is specific to implementation

#### Define the resource: `class ResourceVX(ComponentResource)`
The pulumi component for a data platform resource. Initializes a market client to declare metadata in the market, and declares any other infrastructure needed by the resource.

#### Define resource metadata: `@serde @dataclass class ResourceVXData()`
A dataclass that models the data that will be serialized (with `pyserde`) to the storage provided by the market client. The data class shouldn't define or inherit any attributes that are marked as Pulumi `Inputs` or `Outputs`. It should be used inside an `Output.apply`.

## FAQ/Learnings

#### Typing inputs and outputs to `ComponentResources`
Python's all about type hinting. Two things make this fragile;
* Pulumi reads type annotations to build the input output schemas that are exposed to other languages. There are still a lot of holes in how annotations are read when applying patterns like inheritance and composition.
* Pulumi's required `Input` and `Output` attribute types can be many things; (`type`, `Awaitable[type]`, `ForwardRef[T]`). This wreaks havoc with standard tooling for python data structures (`dataclasses`) and validation (`pydantic`).

So the advice is, keep it veeeery simple and don't believe everything you read in Pulumi's own blog posts :sad-panda:. Use `TypedDicts` to express type annotations, and treat them as `dicts` of `Outputs` whose values you only ever access safely inside of an `apply`. If you're inside of an apply, go wild!

DO:
* Use annotated `TypedDicts` for Pulumi `ComponentResource` inputs (`args` or `properties`). Attributes' type annotations must be wrapped as `Inputs[type]`, or they must be another `TypedDict` with the same constraint.
* On `ComponentResources`, do not include any other class attributes than what you intend to output. They must be wrapped in `Output`, and cannot be complex types (must be `dict`, `str`, `int`, ...). Set the attributes in your `__init__` and then map them in your `register_outputs`.

DON'T:
* Try and do inheritance of `TypedDicts`. Composition with nested `TypedDicts` turned out to be a lot more reliable and probably a better idea.
* Don't use dataclasses for args if you want support from other languages or want to build the dependency graph. The required `Input` wrapping on attributes' type annotations is a long way from supported. For example, `Input[str]` turns into `Union[str], Awaitable[str], ForwardRef[T]]`. All the things we expect from dataclasses, like `dataclasses.asdict`, `pyserde`, `dacit`, ... confused by the `ForwardRef[T]` in the union.

