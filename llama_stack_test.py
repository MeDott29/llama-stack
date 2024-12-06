#!/usr/bin/env python3
import os
from llama_stack_client import LlamaStackClient
import subprocess
from pathlib import Path

def test_llama_stack_environment():
    """Test if the Llama Stack environment is properly configured."""
    try:
        # Check if Docker is running
        subprocess.run(["docker", "info"], check=True, capture_output=True)
        print("✓ Docker is running")
    except subprocess.CalledProcessError:
        print("✗ Docker is not running")
        return False

    # Check for LLAMA_CHECKPOINT_DIR
    checkpoint_dir = os.getenv('LLAMA_CHECKPOINT_DIR')
    if not checkpoint_dir:
        print("✗ LLAMA_CHECKPOINT_DIR not set")
        return False
    print(f"✓ LLAMA_CHECKPOINT_DIR set to: {checkpoint_dir}")

    return True

def test_llama_stack_server():
    """Test if Llama Stack server is running in Docker."""
    try:
        # First check if container exists and get its status
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", "name=llama-stack", "--format", "{{.Status}}"],
            capture_output=True,
            text=True
        )
        status = result.stdout.strip()
        
        if not status:
            print("✗ Llama Stack container not found")
        elif "Up" in status:
            print(f"✓ Llama Stack server is running ({status})")
            return True
        else:
            print(f"✗ Llama Stack container exists but is not running (Status: {status})")
            print("\nTo check container logs:")
            print("   docker logs llama-stack")
            
        # Show startup instructions if not running
        print("\nTo start the server, run:")
        print("1. Remove any existing container:")
        print("   docker rm llama-stack")
        print("\n2. Pull the latest image:")
        print("   docker pull llamastack/distribution-meta-reference-gpu")
        print("\n3. Start the server:")
        print("   docker run -d --name llama-stack --gpus all \\")
        print("     -v $LLAMA_CHECKPOINT_DIR:/checkpoints \\")
        print("     -p 8000:8000 \\")
        print("     llamastack/distribution-meta-reference-gpu")
        return False
    except Exception as e:
        print(f"✗ Error checking Llama Stack server: {e}")
        return False

def test_llama_stack_client():
    """Test connection to Llama Stack server using the official client."""
    try:
        client = LlamaStackClient()
        # Test connection by attempting to get client info
        client_info = client.info()  # Most basic operation
        print("✓ Successfully connected to Llama Stack server")
        print(f"✓ Client info: {client_info}")
        return True
    except Exception as e:
        print(f"✗ Failed to connect to Llama Stack server: {e}")
        return False

def main():
    print("\n=== Llama Stack Environment Test ===\n")
    
    if not test_llama_stack_environment():
        print("\nEnvironment check failed. Please fix the issues above.")
        return

    if not test_llama_stack_server():
        print("\nServer check failed. Please start the Llama Stack server first.")
        return

    if not test_llama_stack_client():
        print("\nClient connection test failed. Please ensure Llama Stack server is running.")
        return

    print("\n=== All Tests Complete ===")

if __name__ == "__main__":
    main() 