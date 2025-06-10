# ruff: noqa: F401

import logging
from dataclasses import dataclass
from typing import Any, Optional, TypedDict

from pulumi import Input, Output, ResourceOptions
from pydantic import create_model
from serde import serde

from shopkeeper.aws.market import AwsMarketV1Client
from shopkeeper.base_producer import Producer, ProducerData

logger = logging.getLogger(__name__)


class AwsProducerV1Args(TypedDict):
    name: Input[str]
    description: Input[str]
    # market: AwsMarketV1Configuration


AwsProducerV1ArgsModel = create_model(
    "AwsProducerV1ArgsModel", **AwsProducerV1Args.__annotations__
)


@serde
@dataclass
class AwsProducerV1Data(ProducerData):
    # this class does nothing
    pass


class AwsProducerV1(Producer):
    producer_data: Output[dict[str, Any]]
    market_client: AwsMarketV1Client

    def __init__(
        self,
        name: str,
        args: AwsProducerV1Args,
        opts: Optional[ResourceOptions] = None,
    ):
        super().__init__(name, args, opts)

        key = self.market_client.get_producer_metadata_key(self.safe_args.name)

        def prepare_producer_data(d) -> AwsProducerV1Data:
            producer_type = self.__class__.__name__
            producer_data = AwsProducerV1Data(
                market=self.safe_args.market,
                producer_type=producer_type,
                name=name,
                description=self.safe_args.description,
                key=key,
                # add any additional fields from d if needed
                **d,
            )
            return producer_data

        # do like this so that we are ready for awaitables
        producer_data: Output[AwsProducerV1Data] = Output.from_input(
            prepare_producer_data({})
        )

        output_data: Output[dict[str, Any]] = (
            self.market_client.declare_resource_metadata(
                data=producer_data, key=key, name=name, opts=None
            )
        )

        self.producer_data = output_data
        self.register_outputs({"producerData": self.producer_data})
