from pulumi.provider.experimental import component_provider_host
from shopkeeper.shopkeeper import Marketplace

if __name__ == "__main__":
    component_provider_host(name="pulumi-shopkeeper", components=[Marketplace])
