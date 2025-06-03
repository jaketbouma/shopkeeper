import pulumi
import pulumi.automation

from shopkeeper.local.market import (
    LocalMarketV1,
    LocalMarketV1Args,
    LocalMarketV1Configuration,
)
from shopkeeper.local.producer import LocalProducerV1, LocalProducerV1Args


def declare_local_market():
    m = LocalMarketV1(
        name="test-local-market",
        args=LocalMarketV1Args(
            name="SomeMarket",
            description="Some description",
            path="/tmp/test",
        ),
        opts=None,
    )
    pulumi.export("marketData", m.market_data)


def declare_local_producer():
    p = LocalProducerV1(
        name="test-local-producer",
        args=LocalProducerV1Args(
            name="SomeProducer",
            description="Some description",
            market=LocalMarketV1Configuration(
                market_type="LocalMarketV1", metadata_file="notyetimplementedtest"
            ),
            color="Red",
        ),
        opts=None,
    )
    pulumi.export("producerData", p.producer_data)


def test_local_market():
    stack = pulumi.automation.create_or_select_stack(
        stack_name="pytest-local-market",
        project_name="test-infra",
        program=declare_local_market,
    )
    up_result = stack.up()
    assert up_result.summary.result == "succeeded"


def test_local_producer():
    stack = pulumi.automation.create_or_select_stack(
        stack_name="pytest-local-market",
        project_name="test-infra",
        program=declare_local_producer,
    )
    up_result = stack.up()
    assert up_result.summary.result == "succeeded"
