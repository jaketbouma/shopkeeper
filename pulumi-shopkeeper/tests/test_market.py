import logging
import os

import pulumi
import pytest
from serde import from_dict
from serde.yaml import from_yaml, to_yaml

import shopkeeper.market as market
from shopkeeper import aws_market, backend_factory
from shopkeeper.aws_market import (  # noqa F401
    AWSBackendConfiguration,
    AWSBackendDeclaration,
)
from shopkeeper.backend_interface import (
    MarketBackend,
    MarketBackendDeclaration,
    MarketData,
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


# some test markets
@pytest.fixture(
    params=[
        AWSBackendDeclaration(
            bucket_prefix="aws-latest-veg",
            backend_type="aws:latest",
            description="Oh yeah veggies",
            tags=tags,
        ),
        AWSBackendDeclaration(
            bucket_prefix="aws-v1-veg",
            backend_type="aws:v1",
            description="Oh yeah veggies",
            tags=tags,
        ),
    ],
    ids=lambda v: v.backend_type,
)
def some_market_backend_declaration(request):
    return request.param


@pytest.fixture()
def some_market_data(
    some_market_backend_declaration: MarketBackendDeclaration, pytestconfig
) -> MarketData:
    backend_type = some_market_backend_declaration.backend_type
    Backend = backend_factory.get(backend_type)
    cache_key = f"veg_market_data/{backend_type}"

    # use a cached backend
    market_data_yaml = pytestconfig.cache.get(cache_key, None)
    if market_data_yaml is not None:
        logger.info(f"Using cached market_data:\n{market_data_yaml}")
        return from_yaml(Backend.MarketData, market_data_yaml)

    # otherwise, declare stack and run pulumi up
    logger.info(f"Declaring backend: {some_market_backend_declaration}")

    def declare_veg_market():
        """
        A simple inline pulumi program to declare a market
        """
        m = market.Market(
            name="veg-market",
            args=some_market_backend_declaration,
        )
        pulumi.export("market_data", m.market_data)

    stack = pulumi.automation.create_or_select_stack(
        stack_name=f"pytest-{backend_type.replace(':', '--')}",
        project_name="test-infra",
        program=declare_veg_market,
    )
    stack.cancel()
    up_result = stack.up()
    logger.info(
        f"pulumi: {up_result.summary.result}\n\t{up_result.summary.resource_changes}"
    )

    # update the cache
    market_data_dict = up_result.outputs["market_data"].value
    market_data = from_dict(Backend.MarketData, market_data_dict)
    market_data_yaml = to_yaml(market_data)
    logger.info(f"Cacheing market_data:\n{market_data_yaml}")
    pytestconfig.cache.set(cache_key, market_data_yaml)

    return market_data


@pytest.fixture()
def some_market_backend(some_market_data: MarketData) -> MarketBackend:
    Backend = backend_factory.get(some_market_data.backend_configuration.backend_type)
    new_backend = Backend(backend_configuration=some_market_data.backend_configuration)
    return new_backend


def test_backend_declaration(some_market_data: MarketData):
    assert some_market_data is not None
    assert some_market_data.backend_configuration is not None


def test_backend_initialization(some_market_backend, some_market_data):
    assert (
        some_market_backend.backend_configuration
        == some_market_data.backend_configuration
    )


def test_backend_type(some_market_data, some_market_backend_declaration):
    assert (
        some_market_data.backend_configuration.backend_type
        == some_market_backend_declaration.backend_type
    )


def test_backend_bucket_prefix(some_market_data, some_market_backend_declaration):
    assert some_market_data.backend_configuration.bucket.startswith(
        some_market_backend_declaration.bucket_prefix
    )
