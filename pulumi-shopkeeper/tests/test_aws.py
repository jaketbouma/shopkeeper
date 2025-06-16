import logging

import pulumi
import pytest

from shopkeeper.aws.market import AwsMarketV1Args, MarketMetadataV1
from shopkeeper.aws.producer import AwsMarketV1Config, AwsProducerV1, AwsProducerV1Args
from shopkeeper.base_producer import ProducerMetadataV1
from shopkeeper.factory import market_factory

from .test_programs import pulumi_up_for_test_programs

logger = logging.getLogger(__name__)

PROJECT_NAME = "test-aws"


@pytest.fixture()
def some_market_outputs(pytestconfig) -> dict[str, str]:
    market_type = "AwsMarketV1"
    name = "producer-test-market"
    args = AwsMarketV1Args(
        metadata=MarketMetadataV1(
            description="pytest market",
            color="red",
            environment="dev",
        ),
        bucket_prefix="pytest-some-red-market",
    )
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
        project_name=PROJECT_NAME,
        program=declare_market,
    )
    up_result = stack.up()

    # update the cache and return a dict (to match yaml flow)
    outputs = {k: v.value for k, v in up_result.outputs.items()}
    pytestconfig.cache.set(cache_key, outputs)
    return outputs


def test_aws_market(some_market_outputs):
    assert "someMarketConfiguration" in some_market_outputs
    assert "someMarketData" in some_market_outputs


def test_aws_producer(some_market_outputs):
    name = "pytest-aws-producer"
    producer_type = "AwsProducerV1"
    stack_name = "aws_test_producer"
    market_configuration = some_market_outputs["someMarketConfiguration"]

    def declare_aws_producer():
        producer = AwsProducerV1(
            name="test-producer",
            args=AwsProducerV1Args(
                metadata=ProducerMetadataV1(
                    name="test-producer", description="Some test producer"
                ),
                market=AwsMarketV1Config(**market_configuration),
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
    test_program_folder = "yaml_test_programs/aws-market-V1/market"

    # check cache
    outputs = pytestconfig.cache.get(key, None)
    if outputs is not None:
        logger.info(f"{stack_name}: using cached outputs:\n{outputs}")
        return outputs

    # run program
    up_result = pulumi_up_for_test_programs(
        stack_name=stack_name, test_program_folder=test_program_folder
    )
    outputs = {k: v.value for k, v in up_result.outputs.items()}

    # update test cache
    pytestconfig.cache.set(key, outputs)
    return outputs


def test_yaml_market(aws_test_market_output):
    assert "someMarketData" in aws_test_market_output
    assert "someMarketConfiguration" in aws_test_market_output


def test_yaml_producer(aws_test_market_output):
    stack_name = "aws_test_producer"
    up_result = pulumi_up_for_test_programs(
        stack_name=stack_name,
        test_program_folder="yaml_test_programs/aws-market-V1/producer",
    )
    output = up_result.outputs["producerData"]
    assert output is not None
