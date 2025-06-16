import json
import logging
import os

import pytest
from pulumi import automation as auto

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


yaml_programs = [
    {
        "stack_name": "aws-market-market",
        "program_folder": "yaml_test_programs/aws-market-V1/market",
    },
    {
        "stack_name": "aws-market-producer",
        "program_folder": "yaml_test_programs/aws-market-V1/producer",
    },
]


def pulumi_up_for_test_programs(stack_name, test_program_folder):
    work_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), test_program_folder)
    )

    # Assert pulumi.yaml exists (case-insensitive)
    assert any(f.lower() == "pulumi.yaml" for f in os.listdir(work_dir)), (
        f"pulumi.yaml not found in {work_dir}"
    )
    stack = auto.create_or_select_stack(
        stack_name=stack_name,
        work_dir=work_dir,
    )
    logger.info(f"{stack_name}: successfully initialized stack")

    logger.info(f"{stack_name}: refreshing stack")
    stack.refresh(on_output=logger.info)
    logger.info(f"{stack_name}: refresh complete")

    up_result = stack.up()
    assert up_result.summary.result == "succeeded"
    logger.info(f"{stack_name}: up OK")
    return up_result


@pytest.fixture(
    params=yaml_programs,
    ids=lambda d: d["stack_name"],
)
def yaml_test_stack(request):
    stack_name = request.param["stack_name"]
    program_folder = request.param["program_folder"]

    work_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), program_folder))

    # Assert pulumi.yaml exists (case-insensitive)
    assert any(f.lower() == "pulumi.yaml" for f in os.listdir(work_dir)), (
        f"pulumi.yaml not found in {work_dir}"
    )

    stack = auto.create_or_select_stack(
        stack_name=stack_name, work_dir=work_dir, project_name="test-infra"
    )
    logger.info("successfully initialized stack")

    logger.info("refreshing stack")
    stack.refresh(on_output=logger.info)
    logger.info("refresh complete")
    return stack


def test_yaml_programs(yaml_test_stack):
    logger.info("updating stack...")
    up_res = yaml_test_stack.up(on_output=logger.info)
    logger.info(
        f"update summary: \n{json.dumps(up_res.summary.resource_changes, indent=4)}"
    )
    assert up_res.summary.result == "succeeded"


def destroy_yaml_test_stacks(yaml_test_stack):
    print("destroying stacks!")
    yaml_test_stack.destroy()
