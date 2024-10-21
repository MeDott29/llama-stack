#!/bin/bash

# Miniconda installer URL (update this if necessary)
MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"

# Installation directory (you can change this if needed)
INSTALL_DIR="$HOME/miniconda3"

echo "Updating system packages..."
sudo apt update -y

echo "Installing required dependencies (curl, bzip2)..."
sudo apt install -y curl bzip2

echo "Downloading Miniconda installer..."
curl -o ~/miniconda.sh -L $MINICONDA_URL

echo "Running the Miniconda installer..."
bash ~/miniconda.sh -b -p $INSTALL_DIR

echo "Removing the installer to save space..."
rm ~/miniconda.sh

echo "Configuring conda environment..."
$INSTALL_DIR/bin/conda init bash

echo "Sourcing bash profile to activate conda..."
source ~/.bashrc

echo "Verifying installation..."
conda --version

echo "Miniconda installation completed successfully!"
