# Brings in the kitchen sink
# https://github.com/pulumi/pulumi-docker-containers/blob/main/docker/pulumi/Dockerfile

FROM pulumi/pulumi:latest


# Provide a build arg with the username
# using your github handle has some advantages with vscode setup
ARG GITHUB_USERNAME=default_username
ARG USER_NAME=$GITHUB_USERNAME
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# Install some dev tools
RUN sh -c "$(curl -fsLS get.chezmoi.io)"
RUN apt-get update -y && \
  DEBIAN_FRONTEND=noninteractive apt-get install -y \
  sudo \
  zsh \
  tree \
  htop \
  vim 
RUN chsh -s /bin/zsh

# Developer group that can sudo
RUN groupadd --gid $USER_GID $USER_NAME \
    && useradd --uid $USER_UID --gid $USER_GID --shell /bin/zsh -m $USER_NAME \
    && mkdir -p /etc/sudoers.d \
    && echo "$USER_NAME ALL=(ALL:ALL) NOPASSWD: ALL" > /etc/sudoers.d/$USER_NAME \
    && chmod 0440 /etc/sudoers.d/$USER_NAME
    
# Recommend to clone repo into devcontainer, it really seems to improve pylance performance.
#   Do this at /workspace/{repo_name}
RUN mkdir /workspace \
    && chown -R $USER_NAME /workspace

# Switch to the dev user
USER $USER_NAME
ENV GITHUB_USERNAME=${GITHUB_USERNAME}
ENV POETRY_VIRTUALENVS_IN_PROJECT=true

# The base container set XDG_CACHE_HOME XDG_CONFIG_HOME to /root/.cache and /root/.config
ENV XDG_CONFIG_HOME=/home/$USER_NAME/.config
ENV XDG_CACHE_HOME=/home/$USER_NAME/.cache
    
# Keep Zsh command history
RUN mkdir -p /workspace/.history/ && touch /workspace/.history/.zsh_history
ENV HISTFILE=/workspace/.history/.zsh_history
ENV HISTSIZE=10000
ENV SAVEHIST=10000

# Make zsh pretty
RUN wget https://github.com/robbyrussell/oh-my-zsh/raw/master/tools/install.sh -O - | zsh || true
RUN git clone --depth=1 https://github.com/romkatv/powerlevel10k.git "${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/themes/powerlevel10k"

WORKDIR /workspace
#RUN git clone https://github.com/jaketbouma/shopkeeper.git
#RUN cd /workspace/shopkeeper/pulumi-shopkeeper && poetry install

VOLUME /workspace
ENTRYPOINT ["/bin/zsh"]
