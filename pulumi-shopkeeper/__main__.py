from pulumi.provider.experimental import component_provider_host

from shopkeeper.generated.components import components

if __name__ == "__main__":
    component_provider_host(
        name="pulumi-shopkeeper",
        components=components,
    )
