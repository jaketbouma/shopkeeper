import logging
import os
from dataclasses import dataclass

from pulumi import Output
from serde import serde
from serde.yaml import to_yaml

from shopkeeper.base_market import (
    Market,
    MarketArgs,
    MarketClient,
    MarketConfiguration,
    MarketData,
)

logger = logging.getLogger(__name__)


@dataclass
class LocalMarketV1Args(MarketArgs):
    path: str


@dataclass
class LocalMarketV1Configuration(MarketConfiguration):
    market_type: str
    # oddly, we must overload market_type here. 2 levels of inheritance doesn't work...
    # BUG(?): ANALOGY: Args is a dataclass, with attribute bird.
    # bird is a dataclass, and a subclass of WingedAnimal.
    # WingedAnimal has WingedAnimal.wingspan.
    # Args.bird.wingspan is not resolved by Pulumi.
    metadata_file: str


@dataclass
@serde
class LocalMarketData(MarketData):
    path: str
    metadata_file: str


class LocalMarketV1(Market):
    market_data: Output[str]

    def __init__(self, name, args: LocalMarketV1Args, opts):
        super().__init__(name, args, opts)

        filename = os.path.join(
            self.safe_args.path, Market.get_market_metadata_key(name=name)
        )

        market_data = LocalMarketData(
            market_name=name,
            market_type=self.__class__.__name__,
            path=self.safe_args.path,
            metadata_file=filename,
        )
        output_market_data = to_yaml(market_data)

        # do nothing...

        self.market_data = Output.from_input(output_market_data)
        self.register_outputs({"marketData": output_market_data})


class LocalMarketClient(MarketClient):
    def __init__(self, market_configuration: LocalMarketV1Configuration):
        super().__init__(market_configuration)
        self.market_name = "fixme"
