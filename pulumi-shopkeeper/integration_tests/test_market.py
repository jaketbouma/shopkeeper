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
    # {"backend": "aws:v1", "backend_declaration": {"prefix": "aws-v1-veg"}},
]
market_backend_ids = [x["backend"] for x in market_backends]


@pytest.fixture(params=market_backends, ids=market_backend_ids)
def veg_market_backend(request, pytestconfig):
    backend = request.param["backend"]
    backend_declaration = request.param["backend_declaration"]

    Backend = market.backend_factory.get(backend)

    backend_configuration = pytestconfig.cache.get(f"test/veg-{backend}", None)
    if backend_configuration is not None:
        return Backend(**backend_configuration)

    def declare_veg_market():
        m = market.Market(
            "veg-market",
            args=market.MarketArgs(
                speciality="Fresh and nutritious vegetables",
                backend=backend,
                backend_declaration=backend_declaration,
            ),
        )
        pulumi.export("backend_configuration", m["backend_configuration"])

    stack = pulumi.automation.create_or_select_stack(
        stack_name="pytest",
        project_name="test-infra",
        program=declare_veg_market,
    )

    up_result = stack.up()
    backend_configuration = up_result.outputs["backend_configuration"].value

    pytestconfig.cache.set(f"test/veg-{backend}", backend_configuration)

    return Backend(**backend_configuration)


def test_veg_market_backend(veg_market_backend):
    assert veg_market_backend is not None
