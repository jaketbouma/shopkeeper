import json
import os
from typing import Any, Dict

import boto3
import market_backend
import pulumi
import pulumi_aws
from pulumi import ResourceOptions

os.environ["AWS_PROFILE"] = "platform"


class AWSMarketBackend(market_backend.MarketBackend):
    def __init__(self, metadata_file_arn):
        self.backend = "AWS"
        self.market_metadata = self._get_json_from_arn(metadata_file_arn)

    @classmethod
    def declare(cls, metadata, prefix: str, **kwargs) -> pulumi.Output:
        producer_key = "/producer/"
        metadata_key = "/metadata/metadata.json"

        bucket = pulumi_aws.s3.BucketV2(
            f"{prefix}-bucket",
            bucket_prefix=prefix,
            force_destroy=True,
            opts=ResourceOptions(),
        )
        pulumi_aws.s3.BucketOwnershipControls(
            f"{prefix}-BucketOwnershipControls",
            bucket=bucket.bucket,
            rule={
                "object_ownership": "ObjectWriter",
            },
            opts=ResourceOptions(parent=bucket),
        )
        producer_folder = pulumi_aws.s3.BucketObject(
            f"{prefix}-producers",
            bucket=bucket.bucket,
            key=producer_key,
            content=None,
            content_type=None,
            opts=ResourceOptions(parent=bucket),
        )

        output_metadata = pulumi.Output.all(
            producer_key=producer_folder.key,
            metadata_key=metadata_key,
            region=bucket.region,
            bucket=bucket.bucket,
            bucket_arn=bucket.arn,
            bucket_url=f"https://s3.{bucket.region}.amazonaws.com/{bucket.bucket}/",
        )

        pulumi_aws.s3.BucketObject(
            f"{prefix}-metadata",
            bucket=bucket.bucket,
            key=metadata_key,
            content=output_metadata.apply(json.dumps),
            content_type="text/json",
            opts=ResourceOptions(parent=bucket),
        )
        return output_metadata

    @staticmethod
    def _get_json_from_arn(file_arn) -> Dict[str, Any]:
        s3 = boto3.client("s3")
        bucket, key = file_arn.rsplit(":", 1)[-1].split("/", 1)
        response = s3.get_object(Bucket=bucket, Key=key)
        return json.loads(response["Body"].read())

    def declare_producer(self):
        raise Exception("Not yet implemented")


market_backend.factory.register("awsV1", AWSMarketBackend)
