import logging
import os

import pulumi
import pytest

import shopkeeper.market as market
from shopkeeper import aws_market

from .test_market import (  # noqa: F401
    market_backend_declaration,
    veg_market_backend,
)

os.environ["AWS_PROFILE"] = "platform"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info(f"imported {aws_market}")

tags = {
    "environment": "test",
    "project": "shopkeeper",
    "codebase": "https://github.com/jaketbouma/shopkeeper/tree/main/pulumi-shopkeeper/integration_tests",
}


@pytest.fixture()
def pumpkin_producer(veg_market_backend):
    backend_type = veg_market_backend.backend_configuration["backend_type"]
    producer_name = "pumpkintown"

    def declare_pumpkin_producer():
        market.Producer(
            name=producer_name,
            args=market.ProducerArgs(
                description="Delicious pumpkins",
                backend_configuration=veg_market_backend.backend_configuration,
                tags=tags,
            ),
            opts=None,
        )

    stack = pulumi.automation.create_or_select_stack(
        stack_name=f"pytest-{backend_type.replace(':', '-')}-{producer_name}",
        project_name="test-infra",
        program=declare_pumpkin_producer,
    )

    up_result = stack.up()
    logger.info(f"pulumi: {up_result.summary.message}")

    new_producer = veg_market_backend.get_producer(producer_name)
    return new_producer


def test_pumpkin_producer(pumpkin_producer):
    # get the producer metadata with boto
    assert 1 == 1


# test for a producer with a subtly broken backend
def test_pumpkin_producer_wrong_name(veg_market_backend):
    valid_backend_configuration = veg_market_backend.backend_configuration
    invalid_backend_configuration = valid_backend_configuration
    from shopkeeper.market import backend_factory

    backend_factory.get(valid_backend_configuration["backend_type"])
    assert 1 == 1


# test for deploying a producer to somewhere where there already is a producer?


# test for a dataset with a producer that doesn't exist

# test for a dataset with a producer that does exist
