import json
import logging
import os

import pulumi
import pytest
from pulumi_aws import s3

os.environ["AWS_PROFILE"] = "platform"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def example_pulumi_program():
    # Create a bucket and expose a website index document
    site_bucket = s3.Bucket(
        "s3-website-bucket",
        website=s3.BucketWebsiteArgs(index_document="index.html")
    )
    index_content = """
    <html>
        <head><title>Hello S3</title><meta charset="UTF-8"></head>
        <body>
            <p>Hello, world!</p>
            <p>Made with ❤️ with <a href="https://pulumi.com">Pulumi</a></p>
        </body>
    </html>
    """

    # Write our index.html into the site bucket
    s3.BucketObject(
        "index",
        bucket=site_bucket.id,  # reference to the s3.Bucket object
        content=index_content,
        key="index.html",  # set the key of the object
        content_type="text/html; charset=utf-8",
    )  # set the MIME type of the file

    # Allow public ACLs for the bucket
    public_access_block = s3.BucketPublicAccessBlock(
        "exampleBucketPublicAccessBlock",
        bucket=site_bucket.id,
        block_public_acls=False,
    )

    # Set the access policy for the bucket so all objects are readable
    s3.BucketPolicy(
        "bucket-policy",
        bucket=site_bucket.id,
        policy=site_bucket.id.apply(
            lambda id: json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": {
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": ["s3:GetObject"],
                        # Policy refers to bucket explicitly
                        "Resource": [f"arn:aws:s3:::{id}/*"],
                    },
                }
            )
        ),
        opts=pulumi.ResourceOptions(depends_on=[public_access_block]),
    )

    # Export the website URL
    pulumi.export("website_url", site_bucket.website_endpoint)


def test_stack():
    stack = None
    stack = pulumi.automation.create_or_select_stack(
        stack_name="integration_tests",
        project_name="integration_tests",
        program=example_pulumi_program,
    )
    logger.info("Refreshing stack")
    stack.refresh(on_output=print)

    logger.info("Taking stack up")
    stack.up(on_output=print)

    logger.info("Taking stack down")
    stack.destroy(on_output=print)
    # stack.destroy()
