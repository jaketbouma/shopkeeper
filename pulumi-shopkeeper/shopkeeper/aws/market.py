import hashlib
import logging
from dataclasses import dataclass
from typing import Optional, Type

import boto3
from pulumi import Output, ResourceOptions
from pulumi_aws import s3 as pulumi_s3
from serde import serde, to_dict
from serde.yaml import from_yaml, to_yaml

from shopkeeper.base_market import (
    Market,
    MarketArgs,
    MarketClient,
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
    region: str
    market_metadata_key: str


@serde
@dataclass(kw_only=True)
class AwsMarketV1Data(MarketData):
    region: str
    bucket: str
    bucket_arn: str
    market_metadata_key: str
    market_configuration: AwsMarketV1Configuration


class AwsMarketV1(Market):
    market_data: Output[dict[str, str]]

    def __init__(self, name, args: AwsMarketV1Args, opts):
        super().__init__(name, args, opts)

        filename = Market.get_market_metadata_key(name=name)

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
            market_type = self.__class__.__name__
            market_data = AwsMarketV1Data(
                market_type=market_type,
                market_name=name,
                market_metadata_key=filename,
                market_configuration=AwsMarketV1Configuration(
                    market_type=market_type,
                    bucket=d["bucket"],
                    region=d["region"],
                    market_metadata_key=filename,
                ),
                **d,
            )
            return market_data

        market_data: Output[AwsMarketV1Data] = Output.all(
            bucket=bucket.bucket,
            region=bucket.region,
            bucket_arn=bucket.arn,
        ).apply(prepare_market_data)

        # serialize to json using pyserde and calculate Etag
        market_data_serialized: Output[str] = market_data.apply(lambda m: to_yaml(m))
        etag: Output[str] = market_data_serialized.apply(
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

        market_data_as_dict: Output[dict[str, str]] = market_data.apply(
            lambda m: to_dict(m)
        )

        self.market_data = market_data_as_dict
        self.register_outputs({"marketData": self.market_data})


class AwsMarketV1Client(MarketClient):
    def __init__(self, market_configuration: AwsMarketV1Configuration):
        super().__init__(market_configuration=market_configuration)

        yaml_market_data = _read_s3_file(
            region=market_configuration.region,
            bucket=market_configuration.bucket,
            key=market_configuration.market_metadata_key,
        )
        self.market_data = from_yaml(AwsMarketV1Data, yaml_market_data)

    def declare_resource_metadata(
        self,
        data: Output[AwsMarketV1Data],
        key: str,
        name: str,
        opts: Optional[ResourceOptions] = None,
    ) -> Output[dict[str, str]]:
        # serialize to json using pyserde and calculate Etag
        data_serialized: Output[str] = data.apply(lambda m: to_yaml(m))
        etag: Output[str] = data_serialized.apply(
            lambda s: hashlib.md5(s.encode()).hexdigest()
        )

        pulumi_s3.BucketObjectv2(
            f"{name}-metadata",
            bucket=self.market_data.bucket,
            key=key,
            content=data_serialized,
            content_type="text/yaml",
            opts=opts,
            etag=etag,
        )

        output_data = data.apply(lambda x: to_dict(x))
        return output_data

    def read_resource_metadata(self, DataType: Type[MarketData], key):
        content = _read_s3_file(
            region=self.market_data.region, bucket=self.market_data.bucket, key=key
        )
        return from_yaml(DataType, content)


def _read_s3_file(region: str, bucket: str, key: str) -> str:
    s3 = boto3.client("s3")
    key = key.lstrip("/")
    logger.info(f"fetching {bucket}/{key}")
    response = s3.get_object(Region=region, Bucket=bucket, Key=key)
    byte_content = response["Body"].read()
    content = byte_content.decode("utf-8")
    return content
