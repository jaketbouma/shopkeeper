from pulumi.provider.experimental import component_provider_host
from shopkeeper.components import Marketplace, Producer

if __name__ == "__main__":
    component_provider_host(name="pulumi-shopkeeper", components=[Marketplace, Producer])
