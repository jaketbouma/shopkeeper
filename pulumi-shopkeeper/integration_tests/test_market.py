import logging
import os

import pulumi
import pytest

import shopkeeper.market as market
from shopkeeper import aws_market

os.environ["AWS_PROFILE"] = "platform"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info(f"imported {aws_market}")

market_backends = [
    {"backend_type": "aws:latest", "backend_declaration": {"prefix": "aws-latest-veg"}},
    # {"backend_type": "aws:v1", "backend_declaration": {"prefix": "aws-v1-veg"}},
]
market_backend_ids = [x["backend_type"] for x in market_backends]

tags = {
    "environment": "test",
    "project": "shopkeeper",
    "codebase": "https://github.com/jaketbouma/shopkeeper/tree/main/pulumi-shopkeeper/integration_tests",
}


@pytest.fixture(params=market_backends, ids=market_backend_ids)
def veg_market_backend(request, pytestconfig):
    backend_type = request.param["backend_type"]
    backend_declaration = request.param["backend_declaration"]
    cache_key = f"veg_market_backend/{backend_type}"

    # use a cached backend
    backend_configuration = pytestconfig.cache.get(cache_key, None)
    if backend_configuration is not None:
        logger.info(f"Using cached backend_configuration: {backend_configuration}")
        new_backend = market.backend_factory.get(backend_type)(**backend_configuration)
        return new_backend

    # otherwise, declare stack and run pulumi up
    logger.info(f"Declaring backend: {backend_declaration}")

    def declare_veg_market():
        """
        A simple inline pulumi program to declare a market
        """
        m = market.Market(
            name="veg-market",
            args=market.MarketArgs(
                description="Fresh and nutritious vegetables",
                backend_type=backend_type,
                backend_declaration=backend_declaration,
                tags=tags,
            ),
        )
        # make these outputs available via the stack
        # pulumi.export("backend_configuration", m.backend_configuration)
        # pulumi.export("backend", m.backend)

    stack = pulumi.automation.create_or_select_stack(
        stack_name=f"pytest-{backend_type.replace(':', '--')}",
        project_name="test-infra",
        program=declare_veg_market,
    )
    up_result = stack.up()
    logger.info(f"pulumi: {up_result.stdout}")

    # update the cache
    backend_configuration = up_result.outputs["backend_configuration"].value
    pytestconfig.cache.set(cache_key, backend_configuration)

    new_backend = market.backend_factory.get(backend_type)(**backend_configuration)
    return new_backend


def test_veg_market_backend(veg_market_backend):
    assert veg_market_backend.metadata is not None


pumpkin_producer_name = "pumpkintown"
pumpkin_producer_metadata = {"product_owner": "pete@pumpkintown.com"}


@pytest.fixture()
def pumpkin_producer(veg_market_backend):
    def declare_pumpkin_producer():
        p = market.Producer(
            name=pumpkin_producer_name,
            args=market.ProducerArgs(
                backend_type=veg_market_backend["metadata"]["backend_type"],
                backend_configuration=veg_market_backend["metadata"][
                    "backend_configuration"
                ],
                metadata=pumpkin_producer_metadata,
                tags=tags,
            ),
        )

    stack = pulumi.automation.create_or_select_stack(
        stack_name=f"pytest-{backend_type.replace(':', '-')}-{pumpkin_producer_name}",
        project_name="test-infra",
        program=declare_pumpkin_producer,
    )

    up_result = stack.up()
    logger.info(f"pulumi: {up_result.summary.message}")

    return pumpkin_producer_name


def test_pumpkin_producer(pumpkin_producer):
    # get the producer metadata with boto
    producer_metadata = market_backend.get_producer(pumpkin_producer_name)
    logger.info(f"producer_metadata: {producer_metadata}")

    assert producer_metadata == pumpkin_producer_metadata
