import logging
import os
from typing import Any

import pulumi
import pytest
from pulumi.runtime.sync_await import _sync_await

from shopkeeper.aws.market import AwsMarketV1Args, MarketMetadataV1
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
                metadata=MarketMetadataV1(
                    description="pytest market",
                    color="yellow",
                    environment="dev",
                ),
                bucket_prefix="pytest-some-market",
            ),
            opts=None,
        ),
        # dict(
        #    market_type="LocalMarketV1",
        #    name="mymarket",
        #    args=LocalMarketV1Args(
        #        name="pytest-some-market",
        #        description="pytest market",
        #        path="/dev/null",
        #    ),
        #    opts=None,
        # ),
    ],
    ids=lambda x: f"{x['market_type']}/{x['name']}",
)
def some_market_inputs(request) -> dict[str, Any]:
    return request.param


@pytest.fixture()
def some_market_outputs(some_market_inputs, pytestconfig) -> dict[str, Any]:
    market_type = some_market_inputs["market_type"]
    name = some_market_inputs["name"]
    args = some_market_inputs["args"]
    cache_key = f"{market_type}/{name}"

    # read from cache
    outputs = pytestconfig.cache.get(cache_key, None)
    if outputs is not None:
        logger.info(f"Using cached market_data:\n{outputs}")
        return outputs

    def declare_market():
        M = market_factory.get_component(market_type=market_type)
        market_component = M(name=name, args=args, opts=None)
        pulumi.export("someMarketData", market_component.market_data)
        pulumi.export("someMarketConfiguration", market_component.market_configuration)

        return None

    stack = pulumi.automation.create_or_select_stack(
        stack_name=f"pytest-{market_type}-{name}",
        project_name="test-infra",
        program=declare_market,
    )
    up_result = stack.up()

    # update the cache and return a dict (to match yaml flow)
    outputs = {k: v.value for k, v in up_result.outputs.items()}
    pytestconfig.cache.set(cache_key, outputs)
    return outputs


def test_markets(some_market_outputs, some_market_inputs):
    assert (
        some_market_outputs["someMarketData"]["market_type"]
        == some_market_inputs["market_type"]
    )
    assert some_market_outputs["someMarketData"]["name"] == some_market_inputs["name"]
    assert some_market_outputs["someMarketConfiguration"] is not None


def test_market_clients(some_market_outputs, some_market_inputs):
    t = some_market_inputs["market_type"]
    MC = market_factory.get_client(t)
    configuration = market_factory.get_configuration(t)(
        **some_market_outputs["someMarketConfiguration"]
    )
    client = MC(market_configuration=configuration)

    def check_client_market_data(d):
        assert d is not None
        assert d.market_type == some_market_inputs["market_type"]
        assert d.name == some_market_inputs["name"]
        assert d.bucket is not None
        assert d.region is not None

    checks = client.market_data.apply(check_client_market_data)
    _sync_await(checks._future)
