from pulumi.provider.experimental import component_provider_host
from shopkeeper.market import Market, Producer

if __name__ == "__main__":
    component_provider_host(name="pulumi-shopkeeper", components=[Market, Producer])
