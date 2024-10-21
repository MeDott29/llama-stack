#!/bin/bash

set -e  # Exit on any error

echo "Updating package list..."
sudo apt update

echo "Installing necessary prerequisites..."
sudo apt install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    software-properties-common \
    gnupg

echo "Adding Docker's official GPG key..."
curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

echo "Adding Docker's APT repository..."
echo \
  "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

echo "Updating package list again..."
sudo apt update

echo "Installing Docker..."
sudo apt install -y docker-ce docker-ce-cli containerd.io

echo "Verifying Docker installation..."
sudo docker --version

echo "Adding your user to the 'docker' group to run Docker without sudo..."
sudo usermod -aG docker $USER

echo "Restarting Docker service..."
sudo systemctl restart docker

echo "Docker installation completed! Please log out and log back in to apply group changes."
