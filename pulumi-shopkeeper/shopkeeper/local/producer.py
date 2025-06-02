import logging
from dataclasses import dataclass
from typing import Optional

from pulumi import Output, ResourceOptions
from serde import serde, to_dict
from serde.yaml import to_yaml

from shopkeeper.base_producer import Producer, ProducerArgs, ProducerData
from shopkeeper.local.market import LocalMarketV1Configuration

logger = logging.getLogger(__name__)


@dataclass
class LocalProducerV1Args(ProducerArgs):
    market: LocalMarketV1Configuration
    color: Optional[str]


@serde
@dataclass
class LocalProducerV1Data(ProducerData):
    color: Optional[str]
    metadata_file: str


class LocalProducerV1(Producer):
    producer_data: Output[dict[str, str]]

    def __init__(
        self,
        name: str,
        args: LocalProducerV1Args,
        opts: Optional[ResourceOptions] = None,
    ):
        super().__init__(name, args, opts)

        filename = self.market_client.get_producer_metadata_key(self.safe_args.name)

        # pretend to do something...

        # prepare output data
        producer_data = LocalProducerV1Data(
            color="red",
            market=self.safe_args.market,
            name=self.safe_args.name,
            description=self.safe_args.description,
            metadata_file=filename,
        )
        serialized_data = to_yaml(producer_data)
        # do nothing with serialized data
        logger.info(f"Created producer\n{serialized_data}")

        dict_data = to_dict(producer_data)

        self.producer_data = Output.from_input(dict_data)
        self.register_outputs({"producerData": Output.from_input(dict_data)})
