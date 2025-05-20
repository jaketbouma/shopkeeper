import json
import logging
import os
from typing import Any, Dict, Optional

import boto3
from pulumi import Output, ResourceOptions
from pulumi_aws import s3 as pulumi_s3

from shopkeeper.backend_interface import MarketBackend

# Laziness, for now.
os.environ["AWS_PROFILE"] = "platform"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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

    SUPPORTED_BACKEND_TYPES = ["aws:v1", "aws:latest"]

    def __init__(
        self,
        backend_type,
        bucket,
        market_metadata_key,
        tags: Optional[Dict] = None,
        **kwargs,
    ):
        market_data = _read_s3_json(bucket=bucket, key=market_metadata_key)
        backend_configuration = {
            "backend_type": backend_type,
            "bucket": bucket,
            "market_metadata_key": market_metadata_key,
        }

        assert market_data["backend_configuration"] == backend_configuration

        # merge tags from market data with client provided tags
        merged_tags = market_data["tags"] or {}
        merged_tags.update(tags or {})

        super().__init__(
            name=market_data["name"],
            backend_configuration=backend_configuration,
            tags=merged_tags,  # client can set their own tags
        )

    @classmethod
    def declare(
        cls,
        name,
        backend_declaration: Dict[
            str, Any
        ],  # move to complex types when Pulumi supports it
        tags: Optional[Dict[str, str]] = None,
        **custom_namespaces: Optional[Dict[str, Dict]],
    ) -> Output[Dict]:
        """
        Declares a market, creating a bucket and metadata file on S3

        Args:
            name (str): The name of the market.
            backend_type (str): The type of backend to use (e.g., "aws:v1").
            bucket_prefix (str): The prefix for the S3 bucket.
            tags (dict, optional): Tags to apply to the resources.
            **metadata: Additional attributes of the market.
        Returns:
            Output: Content of the market metadata file as a pulumi Output[Dict]
        """
        market_metadata_key = super().get_market_metadata_key(
            name=name,
        )
        bucket_prefix = backend_declaration["bucket_prefix"]
        backend_type = backend_declaration["backend_type"]

        if bucket_prefix is None:
            bucket_prefix = name

        # this code supports a known list of backend types
        if backend_type not in cls.SUPPORTED_BACKEND_TYPES:
            raise Exception(
                f"Backend type {backend_type} not supported by {cls.__name__}"
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
            f"{name}-bucket-writer-owns",
            bucket=bucket.bucket,
            rule={
                "object_ownership": "ObjectWriter",
            },
            opts=ResourceOptions(parent=bucket),
        )

        # directly export to pulumi program
        # export(
        #    "backend_configuration",
        #    Output.all(
        #        backend_type=backend_type,
        #        bucket=bucket.bucket,
        #        market_metadata_key=Output.from_input(market_metadata_key),
        #    ),
        # )

        # build the data structure for the metadata file for the market
        def build_json_metadata(d: Dict):
            return {
                "name": name,
                "region": d["region"],
                "bucket": d["bucket"],
                "bucket_url": f"https://s3.{d['region']}.amazonaws.com/{d['bucket']}/",
                "backend_configuration": {
                    "backend_type": backend_type,
                    "bucket": d["bucket"],
                    "market_metadata_key": market_metadata_key,
                },
                "bucket_arn": d["bucket_arn"],
                "tags": tags,
                **custom_namespaces,
                # TODO: bombs when custom_namespaces is not json serializable!
            }

        metadata_content = Output.all(
            bucket=bucket.bucket, region=bucket.region, bucket_arn=bucket.arn
        ).apply(build_json_metadata)

        # declare the metadata file on object storage as a json file
        pulumi_s3.BucketObjectv2(
            f"{name}-metadata-json",
            bucket=bucket.bucket,
            key=market_metadata_key,
            content=metadata_content.apply(json.dumps),
            content_type="text/json",
            opts=ResourceOptions(parent=bucket),
            tags=tags,
        )

        # return exactly what's on object storage as an Output
        return metadata_content

    def declare_producer(
        self,
        name: str,
        opts: Optional[ResourceOptions] = None,
        **custom_namespaces: Dict[str, Dict],
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
        bucket = self.backend_configuration["bucket"]
        producer_key = self.get_producer_metadata_key(name)

        def build_producer_data(d):
            return {**d}

        producer_data = Output.all(
            name=name,
            producer_key=producer_key,
            **custom_namespaces,
        ).apply(build_producer_data)

        # export(f"producer_data/{name}", producer_data)  #     error: pulumi-shopkeeper:index:Producer resource 'pumpkintown' has a problem: Unexpected <class 'Exception'>: Failed to export output. Root resource is not an instance of 'Stack':
        content = producer_data.apply(json.dumps)
        import hashlib

        etag = content.apply(lambda s: hashlib.md5(s.encode()).hexdigest())
        pulumi_s3.BucketObjectv2(
            f"{name}-metadata-json",
            bucket=bucket,
            key=producer_key,
            content=content,
            content_type="text/json",
            opts=opts,
            tags=self.tags,  # add market's tags
            etag=etag,
        )
        return producer_data

    def get_producer(self, name: str):
        producer_key = self.get_producer_metadata_key(name)
        return _read_s3_json(self.backend_configuration["bucket"], producer_key)

    def declare_dataset(
        self,
        name: str,
        opts: Optional[ResourceOptions] = None,
        **custom_namespaces: Dict[str, Dict],
    ) -> Output:
        bucket = self.backend_configuration["bucket"]
        dataset_key = self.get_producer_metadata_key(name)

        def build_dataset_data(d):
            return {**d}

        dataset_data = Output.all(
            name=name,
            dataset_key=dataset_key,
            **custom_namespaces,
        ).apply(build_dataset_data)

        # export(f"dataset_data/{name}", dataset_data)

        pulumi_s3.BucketObjectv2(
            f"{name}-metadata-json",
            bucket=bucket,
            key=dataset_key,
            content=dataset_data.apply(json.dumps),
            content_type="text/json",
            opts=opts,
            tags=self.tags,  # add market's tags
        )
        return dataset_data

    def get_dataset(self, producer_name: str, dataset_name: str):
        dataset_key = self.get_dataset_metadata_key(
            producer_name=producer_name, dataset_name=dataset_name
        )
        return _read_s3_json(self.backend_configuration["bucket"], dataset_key)


def _read_s3_json(bucket: str, key: str) -> Dict[str, Any]:
    s3 = boto3.client("s3")
    key = key.lstrip("/")
    logger.info(f"fetching {bucket}/{key}")
    response = s3.get_object(Bucket=bucket, Key=key)
    byte_content = response["Body"].read()
    content = byte_content.decode("utf-8")
    return json.loads(content)
