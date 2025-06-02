import hashlib
import logging
import os
from dataclasses import dataclass
from typing import Optional

import pulumi_s3
from pulumi import Output, ResourceOptions
from serde import serde, to_dict
from serde.yaml import to_yaml

from shopkeeper.base_market import (
    Market,
    MarketArgs,
    MarketConfiguration,
    MarketData,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass()
class AwsMarketV1Args(MarketArgs):
    bucket_prefix: Optional[str] = None


@serde
@dataclass()
class AwsMarketV1Configuration(MarketConfiguration):
    bucket: str
    market_metadata_key: str


@serde
@dataclass(kw_only=True)
class AwsMarketV1Data(MarketData):
    region: str
    bucket: str
    bucket_url: str
    bucket_arn: str
    market_metadata_key: str


class AwsMarketV1(Market):
    market_data: Output[dict[str, str]]

    def __init__(self, name, args: AwsMarketV1Args, opts):
        super().__init__(name, args, opts)

        filename = os.path.join(
            self.safe_args.path, Market.get_market_metadata_key(name=name)
        )

        # create bucket and set permissions
        bucket = pulumi_s3.BucketV2(
            f"{name}-bucket",
            bucket_prefix=self.safe_args.bucket_prefix,
            force_destroy=True,
            tags=None,
        )
        pulumi_s3.BucketOwnershipControls(
            f"{name}-bucket-writer-owns",
            bucket=bucket.bucket,
            rule={
                "object_ownership": "ObjectWriter",
            },
            opts=ResourceOptions(parent=bucket),
        )

        def prepare_market_data(d) -> AwsMarketV1Data:
            market_data = AwsMarketV1Data(
                market_type=self.__class__.__name__,
                market_name=name,
                market_metadata_key=filename,
                **d,
            )
            return market_data

        market_data: Output[AwsMarketV1Data] = Output.all(
            bucket=bucket.bucket,
            region=bucket.region,
            bucket_url=bucket.url,
            bucket_arn=bucket.arn,
        ).apply(prepare_market_data)

        # serialize to json using pyserde and calculate Etag
        market_data_serialized = market_data.apply(lambda m: to_yaml(m))
        etag = market_data_serialized.apply(
            lambda s: hashlib.md5(s.encode()).hexdigest()
        )

        # declare the metadata file on object storage as a json file
        pulumi_s3.BucketObjectv2(
            f"{name}-metadata-json",
            bucket=bucket.bucket,
            key=market_data.market_metadata_key,
            content=market_data_serialized,
            content_type="text/json",
            opts=ResourceOptions(parent=bucket),
            etag=etag,
        )

        market_data_as_dict = market_data.apply(lambda m: to_dict(m))
        self.market_data = market_data_as_dict
        self.register_outputs({"marketData": self.market_data})
