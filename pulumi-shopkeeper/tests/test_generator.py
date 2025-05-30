import importlib

from pulumi import ComponentResource

from shopkeeper.backend_factory import get_backends
from shopkeeper.component_generator import (
    __clean_generated_components,
    __generate_components,
)


def test_component_generator():
    __clean_generated_components()
    __generate_components()

    generated_module = importlib.import_module("shopkeeper.generated.components")
    for backend in get_backends():
        cls = getattr(generated_module, backend.name, None)
        assert cls is not None, f"Class {cls} not found in generated components"
        assert issubclass(cls, ComponentResource), (
            f"{backend.name} is not a ComponentResource subclass"
        )
