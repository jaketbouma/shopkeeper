import logging

import pulumi
import pytest
from serde import from_dict

from shopkeeper.aws.market import AwsMarketV1Args
from shopkeeper.aws.producer import AwsProducerV1, AwsProducerV1Args
from shopkeeper.factory import market_factory

from .test_programs import pulumi_up_for_test_programs

logger = logging.getLogger(__name__)

PROJECT_NAME = "test-aws"


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
        project_name=PROJECT_NAME,
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
    stack_name = "aws_test_producer"

    def declare_aws_producer():
        producer = AwsProducerV1(
            name="test-producer",
            args=AwsProducerV1Args(
                name=name,
                description="pytest aws producer",
                # market=AwsMarketV1Configuration(**some_market["market_configuration"]),
            ),
        )
        pulumi.export("someProducerData", producer.producer_data)

    stack = pulumi.automation.create_or_select_stack(
        stack_name=stack_name,
        project_name=PROJECT_NAME,
        program=declare_aws_producer,
    )
    up_result = stack.up()
    assert up_result.summary.result == "succeeded"


#
# Test non-python programs
@pytest.fixture()
def aws_test_market_output(pytestconfig):
    key = "someMarketData"
    stack_name = "aws_test_market"

    # check cache
    output = pytestconfig.cache.get(key, None)
    if output is not None:
        logger.info(f"{stack_name}: using cached outputs:\n{output}")
        return output

    # run program
    up_result = pulumi_up_for_test_programs(
        stack_name=stack_name,
        test_program_folder="yaml_test_programs/aws-veg-market/market",
    )
    output = up_result.outputs[key].value

    # update test cache
    pytestconfig.cache.set(key, output)
    return output


def test_yaml_market(aws_test_market_output):
    assert "market_configuration" in aws_test_market_output
    Configuration = market_factory.get_configuration(
        aws_test_market_output["market_configuration"]["market_type"]
    )
    c1 = from_dict(Configuration, aws_test_market_output["market_configuration"])
    assert c1 is not None
    c2 = Configuration(**aws_test_market_output["market_configuration"])
    assert c2 is not None
    assert c1 == c2


def test_yaml_producer(aws_test_market_output):
    stack_name = "aws_test_producer"
    up_result = pulumi_up_for_test_programs(
        stack_name=stack_name,
        test_program_folder="yaml_test_programs/aws-veg-market/producer",
        refresh=False,
    )
    output = up_result.outputs["producerData"]
    assert output is not None
