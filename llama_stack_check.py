#!/usr/bin/env python3
import subprocess
import json
import os
from typing import Dict, List, Tuple

def check_docker_images() -> List[str]:
    """Check for Llama Stack related Docker images."""
    try:
        result = subprocess.run(
            ['docker', 'images', '--format', '{{.Repository}}:{{.Tag}}'],
            capture_output=True, text=True, check=True
        )
        images = result.stdout.strip().split('\n')
        return [img for img in images if 'llama' in img.lower()]
    except subprocess.CalledProcessError:
        return []
    except FileNotFoundError:
        return []

def check_conda_envs() -> Dict[str, List[str]]:
    """Check Conda environments for Llama Stack packages."""
    llama_packages = {
        'llama_stack',
        'llama_stack_client'
    }
    
    env_packages = {}
    
    try:
        # List all conda environments
        result = subprocess.run(
            ['conda', 'env', 'list', '--json'],
            capture_output=True, text=True, check=True
        )
        envs = json.loads(result.stdout)['envs']
        
        for env_path in envs:
            env_name = os.path.basename(env_path)
            if env_name == '':
                env_name = 'base'
                
            # Check packages in each environment
            try:
                pkg_result = subprocess.run(
                    ['conda', 'run', '-n', env_name, 'pip', 'list'],
                    capture_output=True, text=True, check=True
                )
                installed_packages = [
                    line.split()[0].lower() 
                    for line in pkg_result.stdout.split('\n')[2:]
                    if line
                ]
                
                found_packages = [
                    pkg for pkg in llama_packages 
                    if pkg.lower() in installed_packages
                ]
                
                if found_packages:
                    env_packages[env_name] = found_packages
                    
            except subprocess.CalledProcessError:
                continue
                
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        pass
        
    return env_packages

def check_environment_variables() -> Tuple[bool, str]:
    """Check if LLAMA_CHECKPOINT_DIR is set and valid."""
    checkpoint_dir = os.getenv('LLAMA_CHECKPOINT_DIR')
    if not checkpoint_dir:
        return False, "LLAMA_CHECKPOINT_DIR is not set"
    
    if not os.path.exists(checkpoint_dir):
        return False, f"LLAMA_CHECKPOINT_DIR path does not exist: {checkpoint_dir}"
        
    return True, checkpoint_dir

def main():
    print("\n=== Llama Stack Environment Check ===\n")
    
    # Check Docker images
    print("Checking Docker images...")
    llama_images = check_docker_images()
    if llama_images:
        print("Found Llama Stack Docker images:")
        for img in llama_images:
            print(f"  - {img}")
    else:
        print("No Llama Stack Docker images found")
    
    # Check Conda environments
    print("\nChecking Conda environments...")
    env_packages = check_conda_envs()
    if env_packages:
        print("Found Llama Stack packages in these environments:")
        for env_name, packages in env_packages.items():
            print(f"  - {env_name}: {', '.join(packages)}")
    else:
        print("No Llama Stack packages found in Conda environments")
    
    # Check environment variables
    print("\nChecking environment variables...")
    env_valid, env_message = check_environment_variables()
    if env_valid:
        print(f"LLAMA_CHECKPOINT_DIR is properly set to: {env_message}")
    else:
        print(f"Warning: {env_message}")
    
    print("\n=== Check Complete ===")

if __name__ == "__main__":
    main() 