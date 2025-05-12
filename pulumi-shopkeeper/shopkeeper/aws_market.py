import json
import logging
import os
from typing import Any, Dict, Optional

import boto3
from pulumi import Output, ResourceOptions
from pulumi_aws import s3 as pulumi_s3

import shopkeeper.market as market

# Laziness, for now.
os.environ["AWS_PROFILE"] = "platform"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AWSMarketBackend(market.MarketBackend):
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

    def __init__(self, bucket, metadata_key, tags=None):
        metadata_json_data = _read_s3_json(bucket=bucket, key=metadata_key)

        # TODO I think these properties are required for all backends...
        super().__init__(
            name=metadata_json_data.pop("name"),
            backend=metadata_json_data.pop("backend"),
            backend_configuration=metadata_json_data.pop("backend_configuration"),
            tags=tags,  # client can set their own tags
        )
        # slap on the the extra stuff
        self.metadata = metadata_json_data

    @classmethod
    def declare(
        cls,
        name,
        bucket_prefix: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        **metadata,
    ) -> market.MarketBackend:
        """
        First declare (and deploy) infra, then initialize the class

        Args:
            name (str): The name of the market.
            bucket_prefix (str): The prefix for the S3 bucket.
            tags (dict, optional): Tags to apply to the resources.
            **kwargs: Additional keyword arguments.
        Returns:
            AWSMarketBackend: An instance of the AWSMarketBackend class.
        """
        market_metadata_key = super().get_market_metadata_key(
            name=name,
        )
        if bucket_prefix is None:
            bucket_prefix = name

        # create bucket and set permissions
        bucket = pulumi_s3.BucketV2(
            f"{name}-bucket",
            bucket_prefix=bucket_prefix,
            force_destroy=True,
            opts=ResourceOptions(),
            tags=tags,
        )
        pulumi_s3.BucketOwnershipControls(
            f"{name}-bucket-writer-owns",
            bucket=bucket.bucket,
            rule={
                "object_ownership": "ObjectWriter",
            },
            opts=ResourceOptions(parent=bucket),
        )

        def build_json_metadata(d: Dict):
            d = {
                "name": name,
                "region": d["region"],
                "bucket": d["bucket"],
                "bucket_url": f"https://s3.{d['region']}.amazonaws.com/{d['bucket']}/",
                "backend_configuration": {
                    "bucket": d["bucket"],
                    "metadata_key": market_metadata_key,
                },
                "bucket_arn": d["bucket_arn"],
                "tags": tags,
                **metadata,
            }
            return json.dumps(d)

        metadata_json_content = Output.all(
            bucket=bucket.bucket, region=bucket.region, bucket_arn=bucket.arn
        ).apply(build_json_metadata)

        pulumi_s3.BucketObjectv2(
            f"{name}-metadata-json",
            bucket=bucket.bucket,
            key=market_metadata_key,
            content=metadata_json_content,
            content_type="text/json",
            opts=ResourceOptions(parent=bucket),
            tags=tags,
        )
        return cls(bucket=bucket.bucket, metadata_key=market_metadata_key, tags=tags)

    def declare_producer(
        self, name: str, metadata: Dict, opts: Optional[ResourceOptions] = None, **kwargs
    ):
        bucket = self.backend_configuration["bucket"]
        producer_key = self.get_producer_metadata_key(name)

        pulumi_s3.BucketObjectv2(
            f"{name}-metadata-json",
            bucket=bucket,
            key=producer_key,
            content=json.dumps(metadata),
            content_type="text/json",
            opts=opts,
            tags=self.tags,  # add market's tags
        )
        return None

    def get_producer(self, name: str):
        producer_key = self.get_producer_metadata_key(name)
        return _read_s3_json(self.metadata["bucket"], producer_key)

    def declare_dataset(
        self,
        name: str,
        producer_name: str,
        metadata: Dict,
        configuration: Optional[Dict] = None,
        opts: Optional[ResourceOptions] = None,
        **kwargs,
    ):
        bucket = self.metadata["bucket"]
        dataset_key = self.get_dataset_metadata_key(producer_name=producer_name, dataset_name=name)

        # TODO connect to producer, to enforce existence...

        pulumi_s3.BucketObjectv2(
            f"{name}-metadata-json",
            bucket=bucket,
            key=dataset_key,
            content=json.dumps(metadata),
            content_type="text/json",
            opts=opts,
            tags=self.tags,
        )

        #
        # do other stuff with the configuration...

        return

    def get_dataset(self, producer_name: str, name: str):
        dataset_key = self.get_dataset_metadata_key(dataset_name=name, producer_name=producer_name)
        return _read_s3_json(self.metadata["bucket"], dataset_key)


def _read_s3_json(bucket: str, key: str) -> Dict[str, Any]:
    s3 = boto3.client("s3")
    key = key.lstrip("/")
    logger.info(f"fetching {bucket}/{key}")
    response = s3.get_object(Bucket=bucket, Key=key)
    byte_content = response["Body"].read()
    content = byte_content.decode("utf-8")
    return json.loads(content)


market.backend_factory.register("aws:v1", AWSMarketBackend)
market.backend_factory.register("aws:latest", AWSMarketBackend)
