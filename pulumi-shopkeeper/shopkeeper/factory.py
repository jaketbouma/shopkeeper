from shopkeeper.aws.market import (
    AwsMarketV1,
    AwsMarketV1Client,
    AwsMarketV1Configuration,
)
from shopkeeper.base_market import MarketFactory
from shopkeeper.local.market import (
    LocalMarketClient,
    LocalMarketV1,
    LocalMarketV1Configuration,
)

market_factory = MarketFactory()
market_factory.register(
    market=LocalMarketV1,
    client=LocalMarketClient,
    configuration=LocalMarketV1Configuration,
)
market_factory.register(
    market=AwsMarketV1,
    client=AwsMarketV1Client,
    configuration=AwsMarketV1Configuration,
)
