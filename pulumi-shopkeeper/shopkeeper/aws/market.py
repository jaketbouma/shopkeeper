# ruff: noqa: F401
import hashlib
import logging
from dataclasses import asdict, dataclass
from typing import Any, Optional, Type, TypedDict, TypeVar

import boto3
import yaml
from pulumi import Input, Output, ResourceOptions
from pulumi_aws import s3 as pulumi_s3
from serde import serde, to_dict
from serde.yaml import from_yaml, to_yaml

from shopkeeper.base_market import (
    Market,
    MarketClient,
    MarketMetadataV1,
    SerializationMixin,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TSerializable = TypeVar("TSerializable", bound=SerializationMixin)


class AwsMarketV1Args(TypedDict):
    """
    Properties to declare this market.
    """

    metadata: MarketMetadataV1

    # implementation specific args
    bucket_prefix: Optional[Input[str]]


class AwsMarketV1Config(TypedDict):
    """
    Declarations of resources in this marketplace must provide
    these inputs under properties.market
    """

    market_type: Input[str]
    bucket: Input[str]
    region: Input[str]
    market_metadata_key: Input[str]


@serde
@dataclass(kw_only=True)
class AwsMarketV1Data:
    """
    Data that is serialized back and forth to storage.
    We avoid Pulumi Input/Outputs here.
    """

    market_type: str
    name: str
    metadata: dict[str, str]
    configuration: dict[str, Any]
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
        bucket_prefix = args.get("bucket_prefix", None)

        # create bucket and set permissions
        bucket = pulumi_s3.BucketV2(
            f"{name}-bucket",
            bucket_prefix=bucket_prefix,
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

        # Market data
        def prepare_market_data(d) -> AwsMarketV1Data:
            market_data = AwsMarketV1Data(
                market_type=self.__class__.__name__,
                name=name,
                metadata=d["metadata"],
                configuration=AwsMarketV1Config(
                    bucket=d["bucket"],
                    region=d["region"],
                    market_metadata_key=filename,
                ),  # type: ignore
                region=d["region"],
                bucket=d["bucket"],
                bucket_arn=d["bucket_arn"],
            )
            return market_data

        market_data = Output.all(
            bucket=bucket.bucket,
            region=bucket.region,
            bucket_arn=bucket.arn,
            metadata=args["metadata"],
        ).apply(prepare_market_data)

        market_data_serialized = market_data.apply(to_yaml)
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

        market_data_as_dict = market_data.apply(to_dict)
        self.market_data = market_data_as_dict
        self.market_configuration = market_data_as_dict.apply(
            lambda x: x["configuration"]
        )

        self.register_outputs(
            {
                "marketData": self.market_data,
                "marketConfiguration": self.market_configuration,
            }
        )


class AwsMarketV1Client(MarketClient):
    market_configuration: Output[AwsMarketV1Config]
    market_data: Output[AwsMarketV1Data]

    def __init__(self, market_configuration: AwsMarketV1Config):
        super().__init__()
        self.market_configuration = Output.from_input(market_configuration)

        def _load_market(d: dict[str, str]) -> AwsMarketV1Data:
            data = _read_s3_file(**d)
            market_data = from_yaml(AwsMarketV1Data, data)
            return market_data

        self.market_data = Output.all(
            region=market_configuration["region"],
            bucket=market_configuration["bucket"],
            key=market_configuration["market_metadata_key"],
        ).apply(_load_market)

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

        output_data = data.apply(lambda x: x.to_dict())
        return output_data


def _read_s3_file(region: str, bucket: str, key: str) -> str:
    s3 = boto3.client("s3", region_name=region)
    key = key.lstrip("/")
    logger.info(f"fetching {bucket}/{key}")
    response = s3.get_object(Bucket=bucket, Key=key)
    byte_content = response["Body"].read()
    content = byte_content.decode("utf-8")
    return content
