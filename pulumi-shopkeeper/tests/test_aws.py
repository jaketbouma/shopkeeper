import logging

import pulumi
import pytest

from shopkeeper.aws.market import AwsMarketV1Args, AwsMarketV1Configuration
from shopkeeper.aws.producer import AwsProducerV1, AwsProducerV1Args
from shopkeeper.factory import market_factory

logger = logging.getLogger(__name__)


@pytest.fixture()
def some_market(pytestconfig) -> dict[str, str]:
    market_type = "AwsMarketV1"
    name = "producer-test-market"
    args = AwsMarketV1Args(
        name="pytest-some-market",
        description="pytest market",
        bucket_prefix="pytest-some-market",
    )
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


def test_aws_producer(some_market):
    name = "pytest-aws-producer"
    producer_type = "AwsProducerV1"

    def declare_aws_producer():
        producer = AwsProducerV1(
            name="test-producer",
            args=AwsProducerV1Args(
                name=name,
                description="pytest aws producer",
                market=AwsMarketV1Configuration(**some_market["market_configuration"]),
            ),
        )
        pulumi.export("someProducerData", producer.producer_data)

    stack = pulumi.automation.create_or_select_stack(
        stack_name=f"pytest-{producer_type}-{name}",
        project_name="test-infra",
        program=declare_aws_producer,
    )
    up_result = stack.up()
    assert up_result.summary.result == "succeeded"
