from shopkeeper.aws.market import (
    AwsMarketV1,
    AwsMarketV1Client,
    AwsMarketV1Config,
)
from shopkeeper.base_market import MarketFactory

market_factory = MarketFactory()

market_factory.register(
    market=AwsMarketV1,
    client=AwsMarketV1Client,
    configuration=AwsMarketV1Config,
)
