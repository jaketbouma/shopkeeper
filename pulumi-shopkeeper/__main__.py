from pulumi.provider.experimental import component_provider_host

from shopkeeper.aws.market import AwsMarketV1
from shopkeeper.aws.producer import AwsProducerV1

if __name__ == "__main__":
    component_provider_host(
        name="pulumi-shopkeeper",
        components=[AwsMarketV1, AwsProducerV1],
    )
