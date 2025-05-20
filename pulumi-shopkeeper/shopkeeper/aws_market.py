import hashlib
import json
import logging
from typing import Any, Dict, Optional, TypedDict

import boto3
from pulumi import Output, ResourceOptions
from pulumi_aws import s3 as pulumi_s3

from shopkeeper.backend_interface import MarketBackend

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AWSBackendDeclaration(TypedDict):
    bucket_prefix: Optional[str]
    backend_type: str


class AWSBackendConfiguration(TypedDict):
    bucket: str
    backend_type: str
    market_metadata_key: str


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
    def declare_market(
        cls,
        name,
        args,  # TODO: fix type hint without circular import
        opts: Optional[ResourceOptions] = None,
    ) -> Output[Dict]:
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
        bucket_opts = opts
        backend_declaration: AWSBackendDeclaration = args.get("backend_declaration")

        # default the bucket prefix to the resource name
        bucket_prefix = backend_declaration.get("bucket_prefix", name)
        backend_type = backend_declaration["backend_type"]

        # TODO: type safety
        extensions = args.get("extensions", None)

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
            opts=bucket_opts,
            tags=args.get("tags", None),
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
        def build_json_metadata(d: Dict):
            return {
                "name": name,
                "description": args.get("description", None),
                "region": d["region"],
                "bucket": d["bucket"],
                "bucket_url": f"https://s3.{d['region']}.amazonaws.com/{d['bucket']}/",
                "backend_configuration": {
                    "backend_type": backend_type,
                    "bucket": d["bucket"],
                    "market_metadata_key": market_metadata_key,
                },
                "bucket_arn": d["bucket_arn"],
                "tags": args.get("tags", None),
                "extensions": extensions,
            }

        market_data = Output.all(
            bucket=bucket.bucket, region=bucket.region, bucket_arn=bucket.arn
        ).apply(build_json_metadata)

        content = market_data.apply(json.dumps)
        etag = content.apply(lambda s: hashlib.md5(s.encode()).hexdigest())

        # declare the metadata file on object storage as a json file
        pulumi_s3.BucketObjectv2(
            f"{name}-metadata-json",
            bucket=bucket.bucket,
            key=market_metadata_key,
            content=content,
            content_type="text/json",
            opts=ResourceOptions(parent=bucket),
            etag=etag,
            tags=args.get("tags", None),
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
        bucket = self.backend_configuration["bucket"]
        producer_key = self.get_producer_metadata_key(name)

        def build_producer_data(d):
            return {
                "name": name,
                "description": args.get("description", None),
                "bucket": bucket,
                **d,
            }

        producer_data = Output.all(
            producer_key=producer_key,
        ).apply(build_producer_data)

        content = producer_data.apply(json.dumps)
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
            description=description,
            dataset_key=dataset_key,
            **custom_namespaces,
        ).apply(build_dataset_data)

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
