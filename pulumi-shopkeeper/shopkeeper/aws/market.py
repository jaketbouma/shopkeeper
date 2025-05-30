import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

import boto3
from pulumi import Output, ResourceOptions
from pulumi_aws import s3 as pulumi_s3
from serde import serde
from serde.yaml import from_yaml, to_yaml

from shopkeeper.backend_interface import (
    MarketBackend,
    MarketBackendConfiguration,
    MarketBackendDeclaration,
    MarketData,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass(kw_only=True)
class AWSBackendDeclaration(MarketBackendDeclaration):
    bucket_prefix: Optional[str] = None
    # bucket_prefix: str


@serde
@dataclass(kw_only=True)
class AWSBackendConfiguration(MarketBackendConfiguration):
    bucket: str
    market_metadata_key: str


@serde
@dataclass(kw_only=True)
class AWSMarketData(MarketData):
    backend_configuration: AWSBackendConfiguration
    region: str
    bucket: str
    bucket_url: str
    bucket_arn: str


class AWSMarketBackend(MarketBackend):
    """
    A client to interact with the marketplace to;
    1. "declare" markets, producers, consumers and datasets with pulumi-aws
    2. "get" consumers, producers and datasets with boto3

    The Metadata structure on S3;

        market={market-name}/
        ├── metadata.json
        ├── [static html ux]
        ├── producer={producer-name}/
        │   ├── metadata.json
        │   └── dataset={dataset-name}/
        │       └── metadata.json
        └── consumer={consumer-name}/
            ├── metadata.json
            └── [infra declarations, approvals and other documentation]

    The market is deployed separately.
    """

    backend_configuration: Optional[AWSBackendConfiguration] = None
    _serializer = from_yaml
    _deserializer = to_yaml

    BackendConfiguration = AWSBackendConfiguration
    BackendDeclaration = AWSBackendDeclaration
    MarketData = AWSMarketData

    def __init__(
        self,
        backend_configuration: AWSBackendConfiguration,
    ):
        # assuming yaml
        raw_market_data = _read_s3_file(
            bucket=backend_configuration.bucket,
            key=backend_configuration.market_metadata_key,
        )
        market_data = from_yaml(AWSMarketData, raw_market_data)

        super().__init__(
            backend_configuration=backend_configuration, market_data=market_data
        )

    @classmethod
    def declare_market(
        cls, name, backend_declaration: AWSBackendDeclaration
    ) -> Output[Any]:
        """
        Declares a market, creating a bucket and metadata file on S3

        Args:
            name (str): The name of the market.
            description (str): The description of the market.
            backend_declaration (dict): Backend configuration including 'backend_type' and 'bucket_prefix'.
            tags (dict, optional): Tags to apply to the resources.
            extensions (dict, optional): Additional extensions for the market.
        Returns:
            Output: Content of the market metadata file as a pulumi Output[Dict]
        """
        market_metadata_key = super().get_market_metadata_key(
            name=name,
        )

        # default the bucket prefix to the resource name
        if backend_declaration.bucket_prefix is None:
            backend_declaration.bucket_prefix = name

        # create bucket and set permissions
        bucket = pulumi_s3.BucketV2(
            f"{name}-bucket",
            bucket_prefix=backend_declaration.bucket_prefix,
            force_destroy=True,
            tags=backend_declaration.tags,
        )
        pulumi_s3.BucketOwnershipControls(
            f"{name}-bucket-writer-owns",
            bucket=bucket.bucket,
            rule={
                "object_ownership": "ObjectWriter",
            },
            opts=ResourceOptions(parent=bucket),
        )

        # build the data structure for the metadata file for the market
        def build_market_data(d: Dict) -> AWSMarketData:
            backend_configuration = AWSBackendConfiguration(
                backend_type=backend_declaration.backend_type,
                bucket=d["bucket"],
                market_metadata_key=market_metadata_key,
            )
            market_data = AWSMarketData(
                metadata_version="v1",
                backend_configuration=backend_configuration,
                name=name,
                description=backend_declaration.description,
                backend_tags=backend_declaration.tags,
                extensions=backend_declaration.extensions,
                region=d["region"],
                bucket=d["bucket"],
                bucket_url=f"https://s3.{d['region']}.amazonaws.com/{d['bucket']}/",
                bucket_arn=d["bucket_arn"],
            )

            return market_data

        market_data: Output[MarketData] = Output.all(
            bucket=bucket.bucket, region=bucket.region, bucket_arn=bucket.arn
        ).apply(build_market_data)

        # serialize to json using pyserde and calculate Etag
        market_data_serialized = market_data.apply(lambda m: to_yaml(m))
        etag = market_data_serialized.apply(
            lambda s: hashlib.md5(s.encode()).hexdigest()
        )

        # declare the metadata file on object storage as a json file
        pulumi_s3.BucketObjectv2(
            f"{name}-metadata-json",
            bucket=bucket.bucket,
            key=market_metadata_key,
            content=market_data_serialized,
            content_type="text/json",
            opts=ResourceOptions(parent=bucket),
            etag=etag,
            tags=backend_declaration.tags,
        )

        # return exactly what's on object storage as an Output
        return market_data

    def declare_producer(
        self, name: str, args, opts: Optional[ResourceOptions] = None
    ) -> Output[Dict]:
        """
        Declares a producer, creating a metadata object in an S3 bucket.

        Args:
            name (str): The name of the producer.
            opts (Optional[ResourceOptions], optional): Pulumi resource options for the S3 object. Defaults to None.
            **metadata: A json serializable dictionary containing arbitrary metadata for the producer.

        Returns:
            None
        """
        producer_key = self.get_producer_metadata_key(name)

        def build_producer_data(d):
            return {
                "name": name,
                "description": args.get("description", None),
                "bucket": self.backend_configuration.bucket,
                **d,
            }

        producer_data = Output.all(
            producer_key=producer_key,
        ).apply(build_producer_data)

        content = producer_data.apply(json.dumps)
        etag = content.apply(lambda s: hashlib.md5(s.encode()).hexdigest())

        pulumi_s3.BucketObjectv2(
            f"{name}-metadata-json",
            bucket=self.backend_configuration.bucket,
            key=producer_key,
            content=content,
            content_type="text/yaml",
            opts=opts,
            tags=self.backend_tags,  # add market's tags
            etag=etag,
        )
        return producer_data

    def get_producer(self, name: str):
        producer_key = self.get_producer_metadata_key(name)
        return _read_s3_json(self.backend_configuration.bucket, producer_key)

    def declare_dataset(
        self,
        name: str,
        args,
        opts: Optional[ResourceOptions] = None,
    ) -> Output:
        bucket = self.backend_configuration.bucket
        dataset_key = self.get_producer_metadata_key(name)

        def build_dataset_data(d):
            return {"name": name, "description": args.get("description", None), **d}

        dataset_data = Output.all(
            dataset_key=dataset_key,
        ).apply(build_dataset_data)

        pulumi_s3.BucketObjectv2(
            f"{name}-metadata-json",
            bucket=bucket,
            key=dataset_key,
            content=dataset_data.apply(json.dumps),
            content_type="text/json",
            opts=opts,
            tags=self.backend_tags,  # add market's tags
        )
        return dataset_data

    def get_dataset(self, producer_name: str, dataset_name: str):
        dataset_key = self.get_dataset_metadata_key(
            producer_name=producer_name, dataset_name=dataset_name
        )
        return _read_s3_json(self.backend_configuration.bucket, dataset_key)


def _read_s3_json(bucket: str, key: str) -> Dict[str, Any]:
    s3 = boto3.client("s3")
    key = key.lstrip("/")
    logger.info(f"fetching {bucket}/{key}")
    response = s3.get_object(Bucket=bucket, Key=key)
    byte_content = response["Body"].read()
    content = byte_content.decode("utf-8")
    return json.loads(content)


def _read_s3_file(bucket: str, key: str) -> str:
    s3 = boto3.client("s3")
    key = key.lstrip("/")
    logger.info(f"fetching {bucket}/{key}")
    response = s3.get_object(Bucket=bucket, Key=key)
    byte_content = response["Body"].read()
    content = byte_content.decode("utf-8")
    return content
