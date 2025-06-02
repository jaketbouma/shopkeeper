# Notes on Args and ComponentResource declaration

We need to support:
1. `args/properties` required by the interface that are the same for all implementations.
2. Additional `args/properties` special to the implementation.

# Decisions
* 20250522: In the end, after quickly checking that `dataclasses` were supported with Pulumi (kind of looks OK), I thought to try it out!
* 20250528: Not completely clear that `dataclasses` are in fact supported. ComponentResources are evolving quickly, and it's not clear what is and what will be supported. I've decided to go with code generation instead of expecting Pulumi to be able to understand complex types in Python. This will at least put something between my code and the rapidly evolving experimental library.
Regardless what I do, I think `dataclasses` should be supported, and will push for that in [this issue](https://github.com/pulumi/pulumi/issues/19655).

# Notes

## Inheritance with args as `TypedDicts` or `@dataclasses`
Idea: put implementation independent args in a base class and add implementation specific args in subclasses.

Implementation independent logics can be programmed with Generics: typing it with "any subclass of this base class" (`bound` parameter of TypeVars).

Surprisingly, this wasn't possible with `TypedDict`s:
>You cannot enforce that a field of a TypedDict is a subclass of another TypedDict using Python's type system. TypedDict does not support generics in the same way as classes or dataclasses, and type checkers do not enforce or propagate generic constraints for TypedDict fields.

Dataclasses worked out nicely, and also came with canned serialization from the `pyserde` class :)

## Using generics in ComponentResource definitions
Doesn't really work...
```
# market.py
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
```
and 
```
# __main__.py
AWSMarket = Market[AWSBackendDeclaration]
AWSMarket.__name__ = "AWSMarket"

if __name__ == "__main__":
    component_provider_host(
        name="pulumi-shopkeeper",
        components=[AWSMarket],
        namespace="AWS",
    )

```
produces
```
    Exception: ComponentResource 'AWSMarket' requires an argument named 'args' with a type annotation in its __init__ method
    Error: error resolving type of resource fishmarketProd: internal error loading package "pulumi-shopkeeper": Error loading schema from plugin: could not read plugin [/workspaces/shopkeeper/pulumi-shopkeeper/pulumi-resource-pulumi-shopkeeper] stdout: EOF
      on Pulumi.yaml line 24:
```
because `pulumi/provider/experimental/analyzer.py` is doing a `inspect.get_annotations(o)` on `Market[AWSMarketDeclaration]` which is a `<class 'typing._GenericAlias'>`. This doesn't work, and I don't see a way to get the annotations, I feel like I'm doing something stupid here ;o

Should I just define the Pulumi Component resource in the implementation `aws_market.py`? Why not?


## Thinking again about signatures
```python
# Interface as an Abstract Base Class

# Option 1 - dataclass args
def all_implementations_must_do_this(args:ArgsBaseClass) -> ResponseBaseClass:
    ...

# Option 2 - function signatures
def all_implementations_must_do_this(base_arg_1, base_arg_2, **kwargs) -> Dict:
    ...

```

```python
# Implementations in Subclasses

# Option 1 - don't think about the base class args...
def all_implementations_must_do_this(args:ArgsSubClass) -> ResponseSubClass:
    ...

# Option 2 - have to manage changes to the base class args...
def all_implementations_must_do_this(base_arg_1, base_arg_2, subclass_arg1, subclass_arg2, **kwargs) -> Dict:
    ...
```

## Class factories for Component Resource definitions
Could imagine implementing something like this to generate the Pulumi interfaces;
```python
def ComponentClassFactory(
    component_name: str,
    Args,
) -> Type[ComponentResource]:
    class GeneratedComponent(ComponentResource):
        market_data: Output[Any]

        def __init__(
            self,
            name: str,
            args: Args,  # type: ignore
            opts: Optional[ResourceOptions] = None,
        ):
            super().__init__(
                f"pulumi-shopkeeper:index:{component_name}", name, props={}, opts=opts
            )
            self.market_data = {"berry": "blue"}
            self.register_outputs({"marketData": self.market_data})

    GeneratedComponent.__name__ = component_name
    return GeneratedComponent
```
Or something like this
```python
def ComponentClassFactory(
    component_name: str,
    Args,
) -> Type[ComponentResource]:
    marketData: dict[str, str] = {"banana": "yellow"}

    def _constructor(
        self,
        name: str,
        args: Args,  # type: ignore
        opts: Optional[ResourceOptions] = None,
    ):
        ComponentResource.__init__(
            self, f"pulumi-shopkeeper:index:{component_name}", name, props={}, opts=opts
        )

        marketData = {"mango": "orangish"}
        # do something
        self.register_outputs({"marketData": marketData})

    T = type(
        component_name,
        (ComponentResource,),
        {"__init__": _constructor, "marketData": marketData},
    )
    return T
```
...but I think this is asking for trouble, because static code analysis won't be able to understand these types that are generated at runtime.
The docstrings in the `provider/experimental/analyzer.py` warn against this :D

So... even though code generate feels nasty, it might be the simplest and safest. It will keep us out of the corners of what's supported, and should be pretty easy to debug problems with Pulumi. Problems with the component can easily be debugged on the pure python side :man-shrugging:

## So it looks like code generation is the way to go

The interface is where we put all the component agnostic logics.
The backend factory is where we can access all the implementations of the interface.

```mermaid
    comps["Pulumi Components"]
    int["The interface"]
    py["A backend Implementation"]
    up["A user yaml program"]

    up -- "uses" --> comps
    int -- "generates" --> comps
    py -- "implements" --> int
```
Code generation would need to be part of a build step.
