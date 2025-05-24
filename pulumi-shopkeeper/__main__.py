from pulumi.provider.experimental import component_provider_host

from shopkeeper.aws_market import AWSBackendDeclaration
from shopkeeper.market import Market

AWSMarket = Market[AWSBackendDeclaration]
AWSMarket.__name__ = "AWSMarket"

if __name__ == "__main__":
    component_provider_host(
        name="pulumi-shopkeeper",
        components=[AWSMarket],
        namespace="AWS",
    )
