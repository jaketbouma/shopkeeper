import os
from typing import Type

from jinja2 import Environment, FileSystemLoader
from pulumi import ComponentResource

from shopkeeper.aws_market import AWSBackendDeclaration, AWSMarketBackend  # noqa F401
from shopkeeper.backend_interface import MarketBackend  # noqa F401
from shopkeeper.generated import components

MARKET_BACKENDS = {
    "AWSMarketBackendV1": {
        "component_type": AWSMarketBackend,
        "args_type": AWSBackendDeclaration,
    },
    "AWSMarketBackendLatest": {
        "component_type": AWSMarketBackend,
        "args_type": AWSBackendDeclaration,
    },
}


def get(backend_type) -> Type[MarketBackend]:
    if backend_type not in MARKET_BACKENDS:
        raise KeyError("Unknown Backend")
    return MARKET_BACKENDS[backend_type]["component_type"]


def get_components() -> list[ComponentResource]:
    return components.components


def __generate_components():
    """
    Renders the component.py.jinja template with example data and writes to ./generated/components.py
    """
    env = Environment(
        loader=FileSystemLoader(os.path.dirname(__file__)),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("components.py.jinja")
    example_data = {
        "components": [
            {
                "component_module": v["component_type"].__module__,
                "args_type_name": v["args_type"].__name__,
                "component_name": k,
            }
            for k, v in MARKET_BACKENDS.items()
        ]
    }
    rendered = template.render(**example_data)
    project_root = os.path.dirname(os.path.dirname(__file__))
    output_dir = os.path.join(project_root, "shopkeeper/generated")
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "components.py"), "w") as f:
        f.write(rendered)


if __name__ == "__main__":
    __generate_components()
