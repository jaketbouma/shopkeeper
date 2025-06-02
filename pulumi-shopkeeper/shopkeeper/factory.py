from shopkeeper.base_market import MarketFactory
from shopkeeper.local.market import LocalMarketClient, LocalMarketV1

market_factory = MarketFactory()
market_factory.register(market=LocalMarketV1, client=LocalMarketClient)
