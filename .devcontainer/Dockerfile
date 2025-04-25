FROM pulumi/pulumi:latest

# Install golangci-lint
RUN version=1.42.1 \
    && curl -fsSL https://raw.githubusercontent.com/golangci/golangci-lint/master/install.sh | sh -s -- -b /go/bin v$version \
    && golangci-lint version

# Install pulumictl
RUN version=0.0.42 \
    && curl -fsSLO https://github.com/pulumi/pulumictl/releases/download/v$version/pulumictl-v$version-linux-amd64.tar.gz \
    && tar -xzf pulumictl-v$version-linux-amd64.tar.gz --directory /usr/local/bin --no-same-owner pulumictl \
    && rm -f pulumictl-v$version-linux-amd64.tar.gz \
    && pulumictl version

# Things missing from Pulumi's devcontainer starting point
RUN pip install -U pip setuptools
RUN dotnet workload update

# Add non-root user
ARG GITHUB_USERNAME=default_username
ARG USER_NAME=$GITHUB_USERNAME
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USER_NAME \
    && useradd --uid $USER_UID --gid $USER_GID --shell /bin/bash -m $USER_NAME \
    && mkdir -p /etc/sudoers.d \
    && echo "$USER_NAME ALL=(ALL:ALL) NOPASSWD: ALL" > /etc/sudoers.d/$USER_NAME \
    && chmod 0440 /etc/sudoers.d/$USER_NAME

RUN mkdir -p /go/bin \
    && chown -R $USER_NAME: /go \
    && mkdir -p $HOME/.pulumi/bin \
    && chown -R $USER_NAME: $HOME/.pulumi

# Set up my dev tools
RUN sh -c "$(curl -fsLS get.chezmoi.io)"
RUN apt-get update -y && \
  DEBIAN_FRONTEND=noninteractive apt-get install -y \
  zsh \
  tree \
  vim 
RUN chsh -s /bin/zsh
RUN mkdir /commandhistory \
    && touch /commandhistory/.zsh_history \
    && chown -R $USER_NAME /commandhistory
EXPOSE 5678

USER $USER_NAME
ENV GITHUB_USERNAME=${GITHUB_USERNAME}

# The base container sets XDG_CACHE_HOME XDG_CONFIG_HOME specifically for the root user, we can't unset them in a way that vscode will pick up, so we set them to values for the new user.
# Installing go extensions via vscode use these paths so if we just leave it set to /root/.cache we'll get permission errors.
ENV XDG_CONFIG_HOME=/home/$USER_NAME/.config
ENV XDG_CACHE_HOME=/home/$USER_NAME/.cache

ENV POETRY_VIRTUALENVS_IN_PROJECT=true

# Install zsh stuff
RUN wget https://github.com/robbyrussell/oh-my-zsh/raw/master/tools/install.sh -O - | zsh || true
RUN git clone --depth=1 https://github.com/romkatv/powerlevel10k.git "${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/themes/powerlevel10k"


