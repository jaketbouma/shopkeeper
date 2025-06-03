from pulumi.provider.experimental import component_provider_host

from shopkeeper.local.market import LocalMarketV1
from shopkeeper.local.producer import LocalProducerV1

if __name__ == "__main__":
    component_provider_host(
        name="pulumi-shopkeeper",
        components=[LocalMarketV1, LocalProducerV1],
    )
