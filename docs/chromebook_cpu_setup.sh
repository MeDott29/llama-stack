#!/bin/bash

# Ensure Conda is initialized
source ~/miniforge3/etc/profile.d/conda.sh

# Set variables
CONDA_ENV_NAME="llama-stack-cpu"
LLAMA_STACK_REPO="https://github.com/meta-llama/llama-stack.git"
BUILD_NAME="llama-stack-cpu-build"
PORT=5000

# Create and activate Conda environment
echo "Creating and activating Conda environment: $CONDA_ENV_NAME"
conda create -n $CONDA_ENV_NAME python=3.10 -y
conda activate $CONDA_ENV_NAME

# Clone the Llama Stack repository if it doesn't exist
if [ ! -d "llama-stack" ]; then
  echo "Cloning Llama Stack repository"
  git clone $LLAMA_STACK_REPO
fi

# Install Llama Stack in editable mode
cd llama-stack
echo "Installing Llama Stack"
pip install -e .

# Build Llama Stack distribution
echo "Building Llama Stack distribution"
# llama stack build --name $BUILD_NAME

# Configure the distribution
echo "Configuring Llama Stack"
# llama stack configure $BUILD_NAME

# Start the server
echo "Starting the Llama Stack server on port $PORT"
sudo llama stack run $BUILD_NAME --port $PORT

echo "Server started with PID: $SERVER_PID. Test it at http://localhost:$PORT"

# Test the inference client
echo "Testing the inference client"
python -m llama_stack.apis.inference.client localhost $PORT <<EOF
hello world, write me a 2 sentence poem about the moon
EOF

echo "To stop the server, use: kill $SERVER_PID"
