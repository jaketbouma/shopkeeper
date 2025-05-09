# check that $GITHUB_USERNAME is not empty
if [ -z "$GITHUB_USERNAME" ]; then
  echo "GITHUB_USERNAME is not set. Please set it to your GitHub username."
  exit 1
fi

# Create a chezmoi config file that sets histfile variable
mkdir -p ~/.config/chezmoi
# I have templated .zshrc
cat <<EOF > ~/.config/chezmoi/chezmoi.toml
[data]
    histfile = "/workspace/.history"
EOF
  
# Initialize chezmoi
chezmoi init --apply $GITHUB_USERNAME

# Initialize poetry
cd /workspace/shopkeeper/pulumi-shopkeeper && poetry install