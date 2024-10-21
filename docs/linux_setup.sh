#!/bin/bash

set -e  # Exit immediately if a command exits with a non-zero status.

# Constants
ENV_NAME="chrome-llama-stack"
MODEL_NAME="Llama-3.2-1B-Instruct"
HUGGINGFACE_MODEL_REPO="meta-llama/Llama-3.2-1B-Instruct"
LLAMA_STACK_REPO="https://github.com/meta-llama/llama-stack.git"

# Function to activate Conda environment reliably
activate_conda_env() {
    echo "Activating Conda environment: $ENV_NAME"
    source "$(conda info --base)/etc/profile.d/conda.sh"
    conda activate "$ENV_NAME"
}

# Install Miniconda if not already installed
if ! command -v conda &> /dev/null; then
    echo "Miniconda not found. Installing Miniconda..."
    curl -o ~/miniconda.sh -L https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
    bash ~/miniconda.sh -b -p $HOME/miniconda3
    rm ~/miniconda.sh
    export PATH="$HOME/miniconda3/bin:$PATH"
    source ~/.bashrc
fi

# Ensure Conda is updated
echo "Updating Conda..."
conda update -n base -c defaults conda -y

# Create the Conda environment if it doesn't exist
if ! conda env list | grep -q "$ENV_NAME"; then
    echo "Creating Conda environment: $ENV_NAME"
    conda create -n "$ENV_NAME" python=3.10 -y
fi

# Activate the environment
activate_conda_env

# Clone the llama-stack repository if not already cloned
echo "Cloning llama-stack repository..."
mkdir -p ~/local && cd ~/local
if [ ! -d "llama-stack" ]; then
    git clone "$LLAMA_STACK_REPO"
fi
cd llama-stack

# Install llama-stack in editable mode
echo "Installing llama-stack..."
pip install -e .

# Install Hugging Face CLI if needed
pip install huggingface_hub

# Download the Llama model weights
echo "Downloading Llama model weights..."
python - <<EOF
from huggingface_hub import snapshot_download

model_path = snapshot_download(
    repo_id="$HUGGINGFACE_MODEL_REPO",
    cache_dir="$HOME/.llama/models/$MODEL_NAME"
)
print(f"Model downloaded to: {model_path}")
EOF

# Build the Llama Stack
echo "Building Llama Stack distribution..."
llama stack build --name 1b-instruct --image-type conda

# Configure the Llama Stack
echo "Configuring Llama Stack..."
llama stack configure 1b-instruct <<EOF
$MODEL_NAME
n
4096
1
n
n
sqlite
EOF

# Start the Llama Stack server
echo "Starting Llama Stack server..."
llama stack run 1b-instruct --port 5000 &

# Install httpx for testing
pip install httpx

# Test the inference endpoint
echo "Testing Llama Stack inference..."
python - <<EOF
import httpx

response = httpx.post(
    "http://localhost:5000/inference/chat_completion",
    json={"prompt": "Write me a short poem about stars.", "max_tokens": 50}
)
print("Inference Response:", response.json())
EOF

echo "Llama Stack setup completed successfully!"
