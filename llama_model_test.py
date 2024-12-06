#!/usr/bin/env python3
import os
import subprocess
import json
from pathlib import Path

def scan_checkpoint_dir(checkpoint_dir: str) -> list:
    """Scan the checkpoint directory for Meta model folders."""
    models = []
    try:
        # Look specifically in the checkpoints subdirectory
        checkpoints_dir = Path(checkpoint_dir) / "checkpoints"
        if not checkpoints_dir.exists():
            print(f"Warning: {checkpoints_dir} does not exist")
            return models
            
        for item in checkpoints_dir.glob('*'):
            if item.is_dir():
                # Add model even if consolidated.*.pth isn't found, as some models might use different formats
                models.append(item.name)
                
        if models:
            print(f"Found models in {checkpoints_dir}:")
        else:
            print(f"No models found in {checkpoints_dir}")
            
    except Exception as e:
        print(f"Error scanning checkpoint directory: {e}")
    return models

def test_model_in_docker(model_name: str, docker_image: str = "llamastack/distribution-meta-reference-gpu:latest") -> bool:
    """Test if a specific model loads in Docker container."""
    try:
        # Construct Docker run command with proper mounts and environment
        cmd = [
            "docker", "run", "--rm", "--gpus", "all",
            "-e", f"LLAMA_CHECKPOINT_DIR=/checkpoints",
            "-v", f"{os.getenv('LLAMA_CHECKPOINT_DIR')}:/checkpoints",
            docker_image,
            "python3", "-c",
            f"from llama_stack.models import load_model; model = load_model('{model_name}')"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60  # 60 second timeout
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"Timeout while testing {model_name}")
        return False
    except Exception as e:
        print(f"Error testing {model_name}: {e}")
        return False

def main():
    checkpoint_dir = os.getenv('LLAMA_CHECKPOINT_DIR')
    if not checkpoint_dir:
        print("Error: LLAMA_CHECKPOINT_DIR not set")
        return

    print("\n=== Llama Model Scan and Test ===\n")
    
    # Scan for models
    print(f"Scanning {checkpoint_dir} for Meta models...")
    models = scan_checkpoint_dir(checkpoint_dir)
    
    if not models:
        print("No Meta models found in checkpoint directory")
        return
    
    print(f"\nFound {len(models)} model(s):")
    for model in models:
        print(f"  - {model}")
    
    # Test models
    print("\nTesting models in Docker container...")
    for model in models:
        print(f"\nTesting {model}...")
        success = test_model_in_docker(model)
        if success:
            print(f"✓ {model} loaded successfully")
        else:
            print(f"✗ {model} failed to load")
    
    print("\n=== Scan and Test Complete ===")

if __name__ == "__main__":
    main() 