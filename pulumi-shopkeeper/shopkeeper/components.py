import json
import logging
from typing import Any, Dict, Optional, TypedDict

import pulumi
from pulumi import Inputs, ResourceOptions
from pulumi_aws import s3

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MARKET_BACKENDS = {}


def register_market_backend(name):
    def decorator(fn):
        MARKET_BACKENDS[name] = fn
        return fn

    return decorator


def get_market_backend(name):
    if name not in MARKET_BACKENDS:
        raise ValueError(f"Backend '{name}' is not supported")
    return MARKET_BACKENDS[name]


@register_market_backend("AWS")
def aws_market_backend(prefix: str, metadata: Dict = None, parent: str = None):
    bucket = s3.BucketV2(
        f"{prefix}-bucket",
        bucket_prefix=prefix,
        force_destroy=True,
        opts=ResourceOptions(parent=parent),
    )
    s3.BucketOwnershipControls(
        f"{prefix}-BucketOwnershipControls",
        bucket=bucket.bucket,
        rule={
            "object_ownership": "ObjectWriter",
        },
        opts=ResourceOptions(parent=bucket),
    )
    producer_folder = s3.BucketObject(
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
        if metadata is not None:
            m.update(metadata)
        return m

    output_metadata = pulumi.Output.all(
        producer_arn=producer_folder.arn,
        region=bucket.region,
        bucket=bucket.bucket,
        bucket_arn=bucket.arn,
    ).apply(prep_metadata_content)

    output_metadata.apply(json.dumps)

    metadata_file = s3.BucketObject(
        f"{prefix}-metadata",
        bucket=bucket.bucket,
        key=metadata_key,
        content=output_metadata.apply(json.dumps),
        content_type="text/json",
        opts=ResourceOptions(parent=bucket),
    )
    return pulumi.Output.all(
        metadata_file.id, metadata_file.arn, output_metadata
    ).apply(
        lambda args: {
            "metadata_file_provider_id": args[0],
            "metadata_file_arn": args[1],
            **args[2],
        }
    )


class MarketArgs(TypedDict):
    speciality: pulumi.Input[str]
    backend: pulumi.Input[str]


class Market(pulumi.ComponentResource):
    billboard: pulumi.Output[str]
    metadata: pulumi.Output[Dict[str, Any]]

    def __init__(
        self, name: str, args: MarketArgs, opts: Optional[ResourceOptions] = None
    ) -> None:

        super().__init__("pulumi-shopkeeper:index:Market", name, args, opts)

        self.billboard = f"Jake's Fine {args.get('speciality')} Store"
        self.backend = args.get("backend")

        bucket_prefix = name.lower().replace(" ", "")
        self.metadata = get_market_backend(self.backend)(
            prefix=bucket_prefix, metadata={"billboard": self.billboard}, parent=self
        )

        outputs = {
            "billboard": self.billboard,
            "metadata": self.metadata,
        }

        self.register_outputs(outputs)

    @staticmethod
    def get(logical_name, physical_id) -> "Market":
        return Market(logical_name, address=physical_id, billboard="Derp", remote=True)


class ProducerArgs(TypedDict):
    marketStackName: pulumi.Input[str]
    awscloudfile: Optional[pulumi.Input[str]]


def get_market_metadata_from_stack(stack_name):
    market_stack = pulumi.StackReference(stack_name)
    return market_stack.get_output("marketMetadata")


class Producer(pulumi.ComponentResource):
    marketMetadata: pulumi.Output[dict[str, Any]]

    def __init__(
        self, name: str, args: ProducerArgs, opts: Optional[ResourceOptions] = None
    ) -> None:
        super().__init__("pulumi-shopkeeper:index:Producer", name, args, opts)

        # get metadata from the stack output
        self.marketMetadata = get_market_metadata_from_stack(args["marketStackName"])

        self.register_outputs({"marketMetadata": self.marketMetadata})
