# Shopkeeper
Shopkeeper is a python package that implements Data Platform Resources -- data producers, data consumers and datasets -- as custom infrastructure components.
This project is in its early phases, exploring whether Pulumi can provide a rich self service interface to the data platform.

See [honestgrowth.no](https://honestgrowth.super.site/essays/building-the-marketplace) for strategy and design.

![The marketplace data model: data platform resources, their important attributes, and the simple relationships between them.](https://img.notionusercontent.com/s3/prod-files-secure%2Fd0d7ab13-0efd-4682-92e1-e44b62db0124%2F5b4e1c52-85dc-471a-aca4-f5ade3b5b296%2Fimage.png/size/w=1420?exp=1746884433&sig=8E6lWiF15ASyrGppyOwAB3Rd4MsYzpY_7whwHQGSVtM&id=1ceb6707-d891-80e8-b5f2-f543a0784eaf&table=block)

## Trying out the marketplace
Coming soon!

## Contributor setup

Prerequisites:
* Docker
* (recommended) Visual Studio Code, with the [Dev Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) extension
* A test AWS subscription (`aws sso login`)

This project can be tested and developed in a (rather opinionated) devcontainer based on the (rather large) Pulumi/Pulumi image. This image gives us Java, Go, dotnet and python, which we need to build and test pulumi packages across all supported languages.

To get started, build the container yourself, providing your own github handle as an arg. This will be used to create a non-root container user, and is later by the devcontainer configuration.
```sh
export GITHUB_USERNAME="jaketbouma"
cd .devcontainer
docker build -f dev.Dockerfile --build-arg GITHUB_USERNAME=$GITHUB_USERNAME$ -t shopkeeper-dev:latest ./
```

Review the `.devcontainer/devcontainer.json` file. I use [chezmoi](https://www.chezmoi.io/) to sync dotfile configuration and secrets into the development container using a postStartCommand script. This is mostly for terminal cosmetics and to persist terminal history. You can create your own `.devcontainer/${GITHUB_USERNAME}.postStartCommand.sh` and adjust as needed.

Tests can be run from the python project;
```sh
cd pulumi-shopkeeper
poetry install
poetry run pytest
```

Example pulumi programs that use the module can be found in `/example'.
```sh
cd example/marketplace
pulumi up
```

Happy hacking! Drop me an issue if you get stuck!