import os
import shutil
from collections import defaultdict

import pytest  # noqa
from jinja2 import Environment, FileSystemLoader

from shopkeeper.backend_factory import get_backends


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

    imports = defaultdict(list)
    components = []
    for backend in get_backends():
        imports[backend.market_backend.__module__].append(
            backend.market_backend_declaration.__name__
        )
        imports[backend.market_backend.__module__].append(
            backend.market_backend_declaration.__name__
        )
        components.append(
            {
                "name": backend.name,
                "args_type": backend.market_backend_declaration.__name__,
                "repr": f"{backend.name}(args: {backend.market_backend_declaration.__name__})",
            }
        )

    template_data = {"imports": imports, "components": components}
    rendered = template.render(**template_data)

    project_root = os.path.dirname(os.path.dirname(__file__))
    output_dir = os.path.join(project_root, "shopkeeper/generated")
    output_module = os.path.join(output_dir, "components.py")

    comp_list = ",\n\t".join([c["repr"] for c in template_data["components"]])

    print(f"""🤖 Generating classes\n\t{comp_list}\nto {output_module}""")

    os.makedirs(output_dir, exist_ok=True)
    with open(output_module, "w") as f:
        f.write(rendered)


def __clean_generated_components():
    project_root = os.path.dirname(os.path.dirname(__file__))
    output_dir = os.path.join(project_root, "shopkeeper/generated/*.py")
    shutil.rmtree(output_dir, ignore_errors=True)


if __name__ == "__main__":
    __generate_components()
    print("Components generated successfully.")
