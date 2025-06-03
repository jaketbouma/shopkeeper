import logging
import os

import pulumi
import pytest

from shopkeeper.aws.market import AwsMarketV1Args
from shopkeeper.factory import market_factory

logger = logging.getLogger(__name__)


def test_environment():
    assert "AWS_PROFILE" in os.environ


@pytest.fixture(
    params=[
        dict(
            market_type="AwsMarketV1",
            name="mymarket",
            args=AwsMarketV1Args(
                bucket_prefix="pytest-some-market",
                description="pytest market",
                name="pytest-some-market",
            ),
            opts=None,
        ),
    ]
)
def some_market_inputs(request):
    return request.param


def test_declare_markets(some_market_inputs):
    market_type = some_market_inputs["market_type"]
    name = some_market_inputs["name"]
    args = some_market_inputs["args"]

    def declare_market():
        M = market_factory.get_component(market_type=market_type)
        market_component = M(name=name, args=args, opts=None)
        pulumi.export("someMarketData", market_component.market_data)
        return None

    stack = pulumi.automation.create_or_select_stack(
        stack_name=f"pytest-{market_type}-{name}",
        project_name="test-infra",
        program=declare_market,
    )
    up_result = stack.up()
    logger.info(
        f"pulumi: {up_result.summary.result}\n\t{up_result.summary.resource_changes}"
    )
