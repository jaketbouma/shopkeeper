import pulumi
import pulumi.automation


def declare_local_market():
    from shopkeeper.local.market import LocalMarket, LocalMarketArgs

    m = LocalMarket(
        name="test-local-market",
        args=LocalMarketArgs(
            name="SomeMarket",
            description="Some description",
            market_type="LocalMarket",
            path="/tmp/test",
        ),
        opts=None,
    )
    pulumi.export("marketData", m.marketData)


def declare_local_producer():
    from shopkeeper.local.market import (
        LocalMarketConfiguration,
        LocalProducer,
        LocalProducerArgs,
    )

    p = LocalProducer(
        name="test-local-producer",
        args=LocalProducerArgs(
            name="SomeProducer",
            description="Some description",
            market=LocalMarketConfiguration(
                market_type="LocalMarket", metadata_file="/tmp/test"
            ),
            color="Red",
        ),
        opts=None,
    )
    pulumi.export("producerData", p.producerData)


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
