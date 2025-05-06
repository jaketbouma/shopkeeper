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
    {"backend": "aws:latest", "backend_declaration": {"prefix": "aws-latest-veg"}},
    {"backend": "aws:v1", "backend_declaration": {"prefix": "aws-v1-veg"}},
]
market_backend_ids = [x["backend"] for x in market_backends]

tags = {
    "environment": "test",
    "project": "shopkeeper",
    "codebase": "https://github.com/jaketbouma/shopkeeper/tree/main/pulumi-shopkeeper/integration_tests",
}


@pytest.fixture(params=market_backends, ids=market_backend_ids)
def veg_market_backend(request, pytestconfig):
    backend = request.param["backend"]
    backend_declaration = request.param["backend_declaration"]

    # use a cached backend
    backend_parameters = pytestconfig.cache.get(f"test/veg-{backend}", None)
    if backend_parameters is not None:
        logger.info(f"Using cached backend_configuration: {backend_parameters}")
        return backend_parameters

    logger.info(f"Declaring backend: {backend_declaration}")

    def declare_veg_market():
        m = market.Market(
            "veg-market",
            args=market.MarketArgs(
                speciality="Fresh and nutritious vegetables",
                backend=backend,
                backend_declaration=backend_declaration,
                tags=tags,
            ),
        )
        pulumi.export("backend_configuration", m.backend_configuration)
        pulumi.export("backend", m.backend)

    stack = pulumi.automation.create_or_select_stack(
        stack_name=f"pytest-{backend.replace(':', '--')}",
        project_name="test-infra",
        program=declare_veg_market,
    )

    up_result = stack.up()
    logger.info(f"pulumi: {up_result.summary.message}")

    backend_parameters = {
        "backend": backend,
        "backend_configuration": up_result.outputs["backend_configuration"].value,
    }
    pytestconfig.cache.set(f"test/veg-{backend}", backend_parameters)

    return backend_parameters


def test_veg_market_backend(veg_market_backend):
    backend = veg_market_backend["backend"]
    backend_configuration = veg_market_backend["backend_configuration"]
    market_backend = market.backend_factory.get(backend)(**backend_configuration)
    logger.info(f"Initialized {backend} backend with {backend_configuration}")
    assert market_backend.metadata is not None


def test_pumpkin_producer(veg_market_backend):
    backend = veg_market_backend["backend"]
    backend_configuration = veg_market_backend["backend_configuration"]
    market_backend = market.backend_factory.get(backend)(tags=tags, **backend_configuration)
    name = "pumpkintown"
    metadata = {"product_owner": "pete@pumpkintown.com"}

    def declare_pumpkin_producer():
        p = market.Producer(
            name=name,
            args=market.ProducerArgs(
                backend=backend,
                backend_configuration=backend_configuration,
                metadata=metadata,
                tags=tags,
            ),
        )

    stack = pulumi.automation.create_or_select_stack(
        stack_name=f"pytest-{name.replace(':', '--')}",
        project_name="test-infra",
        program=declare_pumpkin_producer,
    )

    up_result = stack.up()
    logger.info(f"pulumi: {up_result.summary.message}")

    # get the producer metadata with boto
    producer_metadata = market_backend.get_producer(name)

    assert producer_metadata == metadata
