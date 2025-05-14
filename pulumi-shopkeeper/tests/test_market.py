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
def veg_market_data(market_backend_declaration, pytestconfig):
    backend_type = market_backend_declaration["backend_type"]

    cache_key = f"veg_market_data/{backend_type}"

    # use a cached backend
    market_data = pytestconfig.cache.get(cache_key, None)
    if market_data is not None:
        logger.info(f"Using cached backend_configuration: {market_data}")
        return market_data

    # otherwise, declare stack and run pulumi up
    logger.info(f"Declaring backend: {market_backend_declaration}")

    def declare_veg_market():
        """
        A simple inline pulumi program to declare a market
        """
        m = market.Market(
            name="veg-market",
            args=market.MarketArgs(
                description="Fresh and nutritious vegetables",
                backend_declaration=market_backend_declaration,
                tags=tags,
            ),
            opts=None,
        )
        pulumi.export("market_data", m.market_data)

    stack = pulumi.automation.create_or_select_stack(
        stack_name=f"pytest-{backend_type.replace(':', '--')}",
        project_name="test-infra",
        program=declare_veg_market,
    )
    stack.cancel()
    up_result = stack.up()
    logger.info(f"pulumi: {up_result.summary}")

    # update the cache
    market_data = up_result.outputs["market_data"].value
    pytestconfig.cache.set(cache_key, market_data)

    return market_data


@pytest.fixture()
def veg_market_backend(veg_market_data):
    new_backend = backend_factory.get(
        veg_market_data["backend_configuration"]["backend_type"]
    )(**veg_market_data["backend_configuration"])
    return new_backend


def test_market_backend_initialization(veg_market_backend, veg_market_data):
    assert (
        veg_market_backend.backend_configuration
        == veg_market_data["backend_configuration"]
    )
    assert (
        veg_market_backend.backend_configuration
        == veg_market_data["backend_configuration"]
    )


def test_veg_market_backend_type(veg_market_data, market_backend_declaration):
    assert (
        veg_market_data["backend_configuration"]["backend_type"]
        == market_backend_declaration["backend_type"]
    )


def test_veg_market_bucket_prefix(veg_market_data, market_backend_declaration):
    assert veg_market_data["backend_configuration"]["bucket"].startswith(
        market_backend_declaration["bucket_prefix"]
    )
