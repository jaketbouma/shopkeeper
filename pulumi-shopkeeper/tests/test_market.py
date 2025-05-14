import logging
import os

import pulumi
import pytest

import shopkeeper.market as market
from shopkeeper import aws_market, backend_factory

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


@pytest.fixture(
    params=[
        {"bucket_prefix": "aws-latest-veg", "backend_type": "aws:latest"},
        {"bucket_prefix": "aws-v1-veg", "backend_type": "aws:v1"},
    ],
    ids=lambda v: v["backend_type"],
)
def market_backend_declaration(request):
    return request.param


@pytest.fixture()
def veg_market_backend(market_backend_declaration, pytestconfig):
    backend_type = market_backend_declaration["backend_type"]

    cache_key = f"veg_market_backend/{backend_type}"

    # use a cached backend
    backend_configuration = pytestconfig.cache.get(cache_key, None)
    if backend_configuration is not None:
        logger.info(f"Using cached backend_configuration: {backend_configuration}")
        new_backend = backend_factory.get(backend_type)(**backend_configuration)
        return new_backend

    # otherwise, declare stack and run pulumi up
    logger.info(f"Declaring backend: {market_backend_declaration}")

    def declare_veg_market():
        """
        A simple inline pulumi program to declare a market
        """
        market.Market(
            name="veg-market",
            args=market.MarketArgs(
                description="Fresh and nutritious vegetables",
                backend_declaration=market_backend_declaration,
                tags=tags,
            ),
            opts=None,
        )

    stack = pulumi.automation.create_or_select_stack(
        stack_name=f"pytest-{backend_type.replace(':', '--')}",
        project_name="test-infra",
        program=declare_veg_market,
    )
    up_result = stack.up()
    logger.info(f"pulumi: {up_result.summary}")

    # update the cache
    backend_configuration = up_result.outputs["backend_configuration"].value
    pytestconfig.cache.set(cache_key, backend_configuration)

    new_backend = backend_factory.get(backend_type)(**backend_configuration)
    return new_backend


def test_veg_market_backend_type(veg_market_backend, market_backend_declaration):
    assert (
        veg_market_backend.backend_configuration["backend_type"]
        == market_backend_declaration["backend_type"]
    )


def test_veg_market_backend_bucket_prefix(
    veg_market_backend, market_backend_declaration
):
    assert veg_market_backend.backend_configuration["bucket"].startswith(
        market_backend_declaration["bucket_prefix"]
    )
