from pulumi.provider.experimental import component_provider_host

from shopkeeper.local.market import LocalMarket, LocalProducer

if __name__ == "__main__":
    component_provider_host(
        name="pulumi-shopkeeper",
        components=[LocalMarket, LocalProducer],
    )
