import logging
import os
from typing import Any

import pulumi
import pytest

from shopkeeper.aws.market import AwsMarketV1Args
from shopkeeper.factory import market_factory
from shopkeeper.local.market import LocalMarketV1Args

logger = logging.getLogger(__name__)


def test_environment():
    assert "AWS_PROFILE" in os.environ


@pytest.fixture(
    params=[
        dict(
            market_type="AwsMarketV1",
            name="mymarket",
            args=AwsMarketV1Args(
                name="pytest-some-market",
                description="pytest market",
                bucket_prefix="pytest-some-market",
            ),
            opts=None,
        ),
        dict(
            market_type="LocalMarketV1",
            name="mymarket",
            args=LocalMarketV1Args(
                name="pytest-some-market",
                description="pytest market",
                path="/dev/null",
            ),
            opts=None,
        ),
    ],
    ids=lambda x: f"{x['market_type']}/{x['name']}",
)
def some_market_inputs(request) -> dict[str, Any]:
    return request.param


@pytest.fixture()
def some_markets(some_market_inputs, pytestconfig) -> dict[str, str]:
    market_type = some_market_inputs["market_type"]
    name = some_market_inputs["name"]
    args = some_market_inputs["args"]
    cache_key = f"{market_type}/{name}"

    # read from cache
    market_data = pytestconfig.cache.get(cache_key, None)
    if market_data is not None:
        logger.info(f"Using cached market_data:\n{market_data}")
        return market_data

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

    # update the cache and return a dict (to match yaml flow)
    market_data = up_result.outputs["someMarketData"].value
    pytestconfig.cache.set(cache_key, market_data)
    return market_data


def test_markets(some_markets, some_market_inputs):
    assert some_markets["market_type"] == some_market_inputs["market_type"]
    assert some_markets["market_name"] == some_market_inputs["name"]
    assert some_markets["market_configuration"] is not None


def test_market_clients(some_markets):
    t = some_markets["market_type"]
    MC = market_factory.get_client(t)
    configuration = market_factory.get_configuration(t)(
        **some_markets["market_configuration"]
    )
    client = MC(market_configuration=configuration)
    assert client is not None
