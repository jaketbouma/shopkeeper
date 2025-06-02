import logging
import os

from pulumi import automation as auto

from tests.test_programs import yaml_programs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("destroy-test-stacks")


def main():
    for stack_cfg in yaml_programs:
        stack_name = stack_cfg["stack_name"]
        program_folder = stack_cfg["program_folder"]
        work_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), program_folder)
        )

        logger.info(f"🔥 Destroying stack {stack_name} in {work_dir}...")
        stack = auto.create_or_select_stack(stack_name=stack_name, work_dir=work_dir)
        stack.destroy(on_output=logger.info)
        logger.info(f"🪦 Destroyed stack {stack_name}")


if __name__ == "__main__":
    main()
