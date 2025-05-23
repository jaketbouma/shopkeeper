
# `TypedDicts` or `@dataclasses`?
Goal: subclass `MarketBackendConfiguration` and `MarketData`classes, adding implementation specific attributes to those required by the `ABC`s in `backend_interface`.
Have strong typing in the `MarketBackend` base class, where it accepts any subclasses of the above mentioned structured types.
Surprisingly, this wasn't possible with `TypedDict`s:
>You cannot enforce that a field of a TypedDict is a subclass of another TypedDict using Python's type system. TypedDict does not support generics in the same way as classes or dataclasses, and type checkers do not enforce or propagate generic constraints for TypedDict fields.

20250522: In the end, after checking that `dataclasses` were supported with Pulumi (kind of looks OK), I thought to try it out!


# Arguments as dataclasses or kwargs?

We need to support:
1. Arguments required by the interface.
2. Arguments required by the implementation of the interface.

Goals:
* An interface with an outer structure that is always the same, that Pulumi can bind to. The Pulumi ComponentResources use the interface.
* The interface is strongly typed so that we have slapping-good tab completion for developers, builtin documentation, and early errors.

```python
# Interface as an Abstract Base Class

# Option 1
def all_implementations_must_do_this(args:ArgsBaseClass) -> ResponseBaseClass:
    ...

# Option 2
def all_implementations_must_do_this(base_arg_1, base_arg_2, **kwargs) -> Dict:
    ...

```

```python
# Implmentations in Subclasses

# Option 1
def all_implementations_must_do_this(args:ArgsSubClass) -> ResponseSubClass:
    ...

# Option 2
@overload
def all_implementations_must_do_this(base_arg_1, base_arg_2, subclass_arg1, subclass_arg2, **kwargs) -> Dict:
    ...
```

Regardless of the chosen option; a factory will 


```
class MarketBackend[
    # Type variables that accept all subclasses
    # Pre 3.12 syntax would be something like:
    #   BaseClassType = TypeVar("BaseClassType", bound=BaseClass))
    MarketBackendConfigurationType: MarketBackendConfiguration,
    MarketBackendDeclarationType: MarketBackendDeclaration,
    MarketDataType: MarketData,
](ABC):
    """
    A market backend stores and serves the metadata that defines data platform
    resources (data producers, consumers and datasets).

    A MarketBackend can be deployed on: AWS S3, Azure Storage, local filesystem and more.
    This abstract base class defines the common interface to these different underlying backends.
    """

    metadata_version: str = "v1"
    _market_data: MarketData[MarketBackendConfigurationType]
    BackendDeclaration: type[MarketBackendDeclarationType]
    BackendConfiguration: type[MarketBackendConfigurationType]
    MarketData: type[MarketDataType]  # type[MarketData]

    @abstractmethod
    def __init__(
        self,
        backend_configuration: MarketBackendConfigurationType,
        market_data: Optional[MarketDataType] = None,
    ):
```