from typing import Optional, TypedDict, Any, Dict
import pulumi
from pulumi import Inputs, ResourceOptions
import logging
import json

from pulumi_aws import s3

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MARKETPLACE_BACKENDS = {}


def register_marketplace_backend(name):
    def decorator(fn):
        MARKETPLACE_BACKENDS[name] = fn
        return fn

    return decorator


def get_marketplace_backend(name):
    if name not in MARKETPLACE_BACKENDS:
        raise ValueError(f"Backend '{name}' is not supported")
    return MARKETPLACE_BACKENDS[name]


@register_marketplace_backend("AWS")
def aws_marketplace_backend(prefix: str, metadata: Dict = None, parent: str = None):
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


class MarketplaceArgs(TypedDict):
    speciality: pulumi.Input[str]
    backend: pulumi.Input[str]


class Marketplace(pulumi.ComponentResource):
    billboard: pulumi.Output[str]
    metadata: pulumi.Output[Dict[str, Any]]

    def __init__(
        self, name: str, args: MarketplaceArgs, opts: Optional[ResourceOptions] = None
    ) -> None:

        super().__init__("pulumi-shopkeeper:index:Marketplace", name, args, opts)

        self.billboard = f"Jake's Fine {args.get("speciality")} Store"
        self.backend = args.get("backend")

        bucket_prefix = name.lower().replace(" ", "")
        self.metadata = get_marketplace_backend(self.backend)(
            prefix=bucket_prefix, metadata={"billboard": self.billboard}, parent=self
        )

        outputs = {
            "billboard": self.billboard,
            "metadata": self.metadata,
        }

        self.register_outputs(outputs)

    @staticmethod
    def get(logical_name, physical_id) -> "Marketplace":
        return Marketplace(
            logical_name, address=physical_id, billboard="Derp", remote=True
        )


class ProducerArgs(TypedDict):
    marketplaceStackName: pulumi.Input[str]
    awscloudfile: Optional[pulumi.Input[str]]


def get_marketplace(backend: str, market_metadata=str):

    s3.BucketObjectv2.get(arn=market["metadata_arn"])
    return None


class Producer(pulumi.ComponentResource):
    marketMetadata: pulumi.Output[dict[str, Any]]

    def __init__(
        self, name: str, args: ProducerArgs, opts: Optional[ResourceOptions] = None
    ) -> None:
        super().__init__("pulumi-shopkeeper:index:Producer", name, args, opts)

        # get metadata from the stack output
        marketplace_stack = pulumi.StackReference(args.get("marketplaceStackName"))
        self.marketMetadata = marketplace_stack.get_output("marketMetadata")

        self.register_outputs({"marketMetadata": self.marketMetadata})
