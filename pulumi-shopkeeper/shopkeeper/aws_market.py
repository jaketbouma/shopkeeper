import json
import logging
import os
from typing import Any, Dict, Optional

import boto3
from pulumi import Output, ResourceOptions
from pulumi_aws import s3 as pulumi_s3

import shopkeeper.market as market

os.environ["AWS_PROFILE"] = "platform"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AWSMarketBackend(market.MarketBackend):
    def __init__(self, bucket, metadata_key, tags=None):
        self.metadata = _read_s3_json(bucket=bucket, key=metadata_key)
        self.tags = tags

    @classmethod
    def declare(cls, name, metadata, bucket_prefix: str, tags=None, **kwargs) -> market.MarketBackend:
        resource_paths = Dict(
            producer_key= "/shopkeeper/market={name}/producer/",
            dataset_key = "/shopkeeper/market={name}/dataset/",
            consumer_key = "/shopkeeper/market={name}/consumer/",
        )

        # create bucket and set permissions
        bucket = pulumi_s3.BucketV2(
            f"{name}-bucket",
            bucket_prefix=bucket_prefix,
            force_destroy=True,
            opts=ResourceOptions(),
            tags=tags,
        )
        pulumi_s3.BucketOwnershipControls(
            f"{prefix}-BucketOwnershipControls",
            bucket=bucket.bucket,
            rule={
                "object_ownership": "ObjectWriter",
            },
            opts=ResourceOptions(parent=bucket),
        )

        # top level folder for each resource
        for resource_path in [resource_paths]:
            pulumi_s3.BucketObjectv2(
                f"{prefix}-producers",
                bucket=bucket.bucket,
                key=resource_path,
                content=None,
                content_type=None,
                opts=ResourceOptions(parent=bucket),
                tags=tags,
            )

        def clean_output_metadata(d: Dict):
            return {
                "region": d["region"],
                "bucket": d["bucket"],
                "bucket_url": f"https://s3.{d['region']}.amazonaws.com/{d['bucket']}/",
                "backend_configuration": {"bucket": d["bucket"], "metadata_key": metadata_key},
                "bucket_arn": d["bucket_arn"],
                **resource_paths,
            }

        output_dict = Output.all(
            bucket=bucket.bucket, region=bucket.region, bucket_arn=bucket.arn
        ).apply(clean_output_metadata)

        pulumi_s3.BucketObjectv2(
            f"{prefix}-metadata",
            bucket=bucket.bucket,
            key=metadata_key,
            content=output_dict.apply(json.dumps),
            content_type="text/json",
            opts=ResourceOptions(parent=bucket),
            tags=tags,
        )
        return cls(bucket_key=bucket.bucket, metadata=metadata_key)

    def declare_producer(
        self, name: str, metadata: Dict, opts: Optional[ResourceOptions] = None, **kwargs
    ):
        bucket = self.metadata["bucket"]
        producer_key = self._get_producer_key(name)

        pulumi_s3.BucketObjectv2(
            f"{name}-metadata-object",
            bucket=bucket,
            key=producer_key,
            content=json.dumps(metadata),
            content_type="text/json",
            opts=opts,
            tags=self.tags,
        )
        return None

    def get_producer(self, name: str):
        producer_key = self._get_producer_key(name)
        return _read_s3_json(self.metadata["bucket"], producer_key)

    def _get_producer_key(self, name):
        return f"{self.metadata['producer_key'].rstrip('/')}/producer={name}/metadata.json"

    def declare_dataset(
        self,
        name: str,
        metadata: Dict,
        configuration: Dict,
        opts: Optional[ResourceOptions] = None,
        **kwargs,
    ):
        bucket = self.metadata["bucket"]
        producer_key = self._get_producer_key(name)

        pulumi_s3.BucketObjectv2(
            f"{name}-metadata-object",
            bucket=bucket,
            key=producer_key,
            content=json.dumps(metadata),
            content_type="text/json",
            opts=opts,
            tags=self.tags,
        )

        #
        # do other stuff with the configuration...

    def _get_dataset_key(self, name):
        return f"{self.metadata['dataset_key'].rstrip('/')}/dataset={name}/{name}.json"

    def get_dataset(self, name: str):
        dataset_key = self._get_dataset_key(name)
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
