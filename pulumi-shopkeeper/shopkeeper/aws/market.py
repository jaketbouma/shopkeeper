# ruff: noqa: F401
import hashlib
import logging
from dataclasses import asdict, dataclass
from typing import Any, Optional, Type

import boto3
import yaml
from pulumi import Input, Output, ResourceOptions
from pulumi_aws import s3 as pulumi_s3

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


@dataclass(kw_only=True)
class AwsMarketV1Configuration(MarketConfiguration):
    # market_type: Input[str]  # must explicitly overload
    bucket: Input[str]
    region: Input[str]
    market_metadata_key: Input[str]


@dataclass(kw_only=True)
class AwsMarketV1Data(MarketData):
    region: str
    bucket: str
    bucket_arn: str


class AwsMarketV1(Market):
    # need to explicitly mention these for languages other than python
    market_data: Output[dict[str, str]]
    market_configuration: Output[dict[str, str]]

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

        # Market configuration
        def prepare_market_configuration(d) -> dict[str, Any]:
            market_configuration = AwsMarketV1Configuration(
                market_type=self.__class__.__name__, market_metadata_key=filename, **d
            )
            market_configuration_dict = market_configuration.to_dict()
            return market_configuration_dict

        self.market_configuration = Output.all(
            bucket=bucket.bucket,
            region=bucket.region,
        ).apply(prepare_market_configuration)

        # Market data
        def prepare_market_data(d) -> AwsMarketV1Data:
            market_type = self.__class__.__name__
            market_data = AwsMarketV1Data(
                market_type=market_type,
                name=name,
                **d,
            )
            return market_data

        market_data = Output.all(
            bucket=bucket.bucket,
            region=bucket.region,
            bucket_arn=bucket.arn,
            description=self.safe_args.description,
        ).apply(prepare_market_data)

        market_data_serialized = market_data.apply(lambda m: m.to_yaml())
        etag = market_data_serialized.apply(
            lambda s: hashlib.md5(s.encode()).hexdigest()
        )

        # declare the metadata file on object storage as a json file
        pulumi_s3.BucketObjectv2(
            f"{name}-metadata-json",
            bucket=bucket.bucket,
            key=filename,
            content=market_data_serialized,
            content_type="text/json",
            opts=ResourceOptions(parent=bucket),
            etag=etag,
        )

        market_data_as_dict = market_data.apply(asdict)
        self.market_data = market_data_as_dict

        self.register_outputs(
            {
                "marketData": self.market_data,
                "marketConfiguration": self.market_configuration,
            }
        )


class AwsMarketV1Client(MarketClient):
    market_configuration: AwsMarketV1Configuration
    market_data: AwsMarketV1Data

    def __init__(self, market_configuration: AwsMarketV1Configuration):
        super().__init__(market_configuration=market_configuration)

        yaml_market_data = _read_s3_file(
            region=market_configuration.region,
            bucket=market_configuration.bucket,
            key=market_configuration.market_metadata_key,
        )
        self.market_data = AwsMarketV1Data.from_yaml(yaml_market_data)

    def declare_resource_metadata(
        self,
        data: Output[Any],
        key: str,
        name: str,
        opts: Optional[ResourceOptions] = None,
    ) -> Output[dict[str, Any]]:
        # serialize to yaml and calculate Etag
        data_serialized: Output[str] = data.apply(lambda m: m.to_yaml())
        etag: Output[str] = data_serialized.apply(
            lambda s: hashlib.md5(s.encode()).hexdigest()
        )

        pulumi_s3.BucketObjectv2(
            f"{name}-metadata",
            bucket=self.market_configuration.bucket,
            key=key,
            content=data_serialized,
            content_type="text/yaml",
            opts=opts,
            etag=etag,
        )

        output_data = data.apply(lambda x: output_to_dict(x))
        return output_data

    def read_resource_metadata(self, DataType: Type[MarketData], key):
        content = _read_s3_file(
            region=self.market_data.region, bucket=self.market_data.bucket, key=key
        )
        return from_yaml(DataType, content)


def _read_s3_file(region: str, bucket: str, key: str) -> str:
    s3 = boto3.client("s3", region_name=region)
    key = key.lstrip("/")
    logger.info(f"fetching {bucket}/{key}")
    response = s3.get_object(Bucket=bucket, Key=key)
    byte_content = response["Body"].read()
    content = byte_content.decode("utf-8")
    return content
