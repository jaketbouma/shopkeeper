import logging
from dataclasses import dataclass
from typing import Any, Optional, TypedDict

from pulumi import Input, Output, ResourceOptions
from serde import serde, to_dict

from shopkeeper.aws.market import AwsMarketV1Config
from shopkeeper.base_producer import Producer, ProducerMetadataV1

logger = logging.getLogger(__name__)


class AwsProducerV1Args(TypedDict):
    market: Input[AwsMarketV1Config]
    metadata: Input[ProducerMetadataV1]


@serde
@dataclass
class AwsProducerV1Data:
    name: str
    type: str
    metadata: dict[str, Any]  # ProducerMetadataV1
    market: dict[str, Any]  # AwsMarketV1Config


class AwsProducerV1(Producer):
    producer_data: Output[dict[str, Any]]
    # market_client: AwsMarketV1Client
    # market_type: str = "AwsMarketV1"

    def __init__(
        self,
        name: str,
        args: AwsProducerV1Args,
        opts: Optional[ResourceOptions] = None,
    ):
        self.market_type = "AwsMarketV1"

        super().__init__(name, args, opts)

        key = self.market_client.get_producer_metadata_key(name)

        def prepare_producer_data(d) -> AwsProducerV1Data:
            producer_data = AwsProducerV1Data(
                name=name,
                type=self.__class__.__name__,
                market=d["market"],
                metadata=d["metadata"],
            )
            return producer_data

        producer_data = Output.all(
            metadata=args["metadata"], market=args["market"]
        ).apply(prepare_producer_data)

        self.producer_data = producer_data.apply(to_dict)
        self.register_outputs({"producerData": self.producer_data})
