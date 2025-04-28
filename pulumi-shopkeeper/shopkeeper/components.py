from typing import Optional, TypedDict
import pulumi
from pulumi import Inputs, ResourceOptions
import logging

from pulumi_aws import s3

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MarketplaceArgs(TypedDict):
    address: pulumi.Input[str]
    speciality: pulumi.Input[str]


class Marketplace(pulumi.ComponentResource):
    billboard: pulumi.Output[str]
    address: pulumi.Output[str]

    def __init__(
        self, name: str, args: MarketplaceArgs, opts: Optional[ResourceOptions] = None
    ) -> None:

        super().__init__("pulumi-shopkeeper:index:Marketplace", name, args, opts)

        self.billboard = f"Jake's Fine {args.get("speciality")} Store"
        self.address = args.get("address")

        bucket_prefix = name.lower().replace(' ', '')

        self.bucket = s3.BucketV2(
            f"{bucket_prefix}-bucket",
            bucket_prefix=bucket_prefix,
            force_destroy=True,
            opts=ResourceOptions(parent=self),
        )
        bucket_ownership_controls = s3.BucketOwnershipControls(
            f"{bucket_prefix}-BucketOwnershipControls",
            bucket=self.bucket.bucket,
            rule={
                "object_ownership": "BucketOwnerPreferred",
            },
            opts=ResourceOptions(parent=self.bucket),
        )

        self.register_outputs({
            "billboard": self.billboard,
            "address": self.address,
            "bucketid": self.bucket.id
            }
        )

    
    @staticmethod
    def get(logical_name, physical_id) -> 'Marketplace':
        return Marketplace(logical_name, address=physical_id, billboard="Derp", remote=True)



class ProducerArgs(TypedDict):
    marketplaceAddress: pulumi.Input[str]
    parentUrn: Optional[pulumi.Input[str]]


class Producer(pulumi.ComponentResource):
    def __init__(
        self, name: str,
        args: ProducerArgs, opts: Optional[ResourceOptions] = None,
        marketplace=None
    ) -> None:
        opts = ResourceOptions(parent=marketplace)
        super().__init__("pulumi-shopkeeper:index:Producer", name, args, opts)

        #marketplace = Marketplace.get(logical_name=f"{name}-marketplace", physical_id=args.get("address"))

        self.register_outputs({})

