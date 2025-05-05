import json
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, TypedDict

import boto3
import pulumi
import pulumi_aws
from pulumi import ResourceOptions

os.environ["AWS_PROFILE"] = "platform"


class MarketBackend(ABC):
    metadata: Dict[str, Any]

    def __init__(self, **kwargs):
        self.metadata = kwargs

    @abstractmethod
    def declare(self) -> pulumi.Output:
        pass

    @abstractmethod
    def get_market():
        pass


class MarketBackendFactory:
    @staticmethod
    def from_market_property(market_property):
        return MARKET_BACKENDS[market_property["backend"]](**market_property)

    def declare():
        return MARKET_BACKENDS


class AWSMarketBackend(MarketBackend):
    def __init__(self, **kwargs):
        self.backend = "AWS"
        self.metadata = kwargs

    @staticmethod
    def declare(market_properties, prefix: str) -> pulumi.Output:
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
            key="/producer/",
            content=None,
            content_type=None,
            opts=ResourceOptions(parent=bucket),
        )

        metadata_key = "/metadata/metadata.json"

        def prep_metadata_content(args):
            m = {"backend": "AWS", "version": "v0.0.0"}
            m["metadata_url"] = (
                f"https://s3.{args['region']}.amazonaws.com/{args['bucket']}/{metadata_key}"
            )
            m["bucket_arn"] = args["bucket"]
            m["region"] = args["region"]
            m["producer_arn"] = args["producer_arn"]
            if self.metadata is not None:
                m.update(self.metadata)
            return m

        output_metadata = pulumi.Output.all(
            producer_arn=producer_folder.arn,
            region=bucket.region,
            bucket=bucket.bucket,
            bucket_arn=bucket.arn,
        ).apply(prep_metadata_content)

        output_metadata.apply(json.dumps)

        metadata_file = pulumi_aws.s3.BucketObject(
            f"{prefix}-metadata",
            bucket=bucket.bucket,
            key=metadata_key,
            content=output_metadata.apply(json.dumps),
            content_type="text/json",
            opts=ResourceOptions(parent=bucket),
        )
        return pulumi.Output.all(metadata_file.id, metadata_file.arn, output_metadata).apply(
            lambda args: {
                "metadata_file_provider_id": args[0],
                "metadata_file_arn": args[1],
                **args[2],
            }
        )

    @staticmethod
    def get_market(metadata_file_arn) -> Dict[str, Any]:
        s3 = boto3.client("s3")
        bucket, key = metadata_file_arn.rsplit(":", 1)[-1].split("/", 1)
        response = s3.get_object(Bucket=bucket, Key=key)
        return json.loads(response["Body"].read())

    def declare_producer(self):
        raise Exception("Not yet implemented")


MARKET_BACKENDS = {"awsV1": AWSMarketBackend}


class MarketArgs(TypedDict):
    speciality: pulumi.Input[str]
    backend: pulumi.Input[str]
    backend_configuration: Optional[pulumi.Input[Dict[str, Any]]]


class Market(pulumi.ComponentResource):
    billboard: pulumi.Output[str]
    metadata: pulumi.Output[Dict[str, Any]]

    def __init__(
        self,
        name: str,
        args: MarketArgs,
        opts: Optional[ResourceOptions] = None,
    ) -> None:
        super().__init__("pulumi-shopkeeper:index:Market", name, args, opts)
        self.billboard = f"Jake's Fine {args.get('speciality')} Store"
        self.backend = args.get("backend")

        bucket_prefix = name.lower().replace(" ", "")
        self.metadata = Market(self.backend)(
            prefix=bucket_prefix,
            metadata={"billboard": self.billboard},
            parent=self,
        )

        outputs = {
            "billboard": self.billboard,
            "metadata": self.metadata,
        }

        self.register_outputs(outputs)
