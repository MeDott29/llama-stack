# Directory structure:
# llama_env_checker/
# ├── setup.py
# ├── README.md
# ├── llama_env_checker/
# │   ├── __init__.py
# │   ├── checker.py
# │   ├── gpu_utils.py
# │   └── startup.py

# setup.py
from setuptools import setup, find_packages

setup(
    name="llama_env_checker",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "torch>=2.0.0",
        "nvidia-ml-py3>=7.352.0"
    ],
    entry_points={
        'console_scripts': [
            'llama-check=llama_env_checker.startup:main',
        ],
    },
    author="Your Name",
    description="A startup environment checker for Llama Stack deployments",
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    python_requires='>=3.8',
)

# README.md
"""
# Llama Environment Checker

An automated environment checker for Llama Stack deployments that runs during startup.

## Features
- Checks Docker images and Conda environments
- Verifies GPU availability and memory
- Validates environment variables
- Monitors model checkpoint directories
- Supports multi-GPU configurations

## Installation
```bash
pip install llama-env-checker
```

## Usage
Run manually:
```bash
llama-check
```

Add to startup:
```bash
# Add to your .bashrc or startup script
llama-check --startup
```
"""

# llama_env_checker/__init__.py
from .checker import run_checks
from .gpu_utils import check_gpu_memory

__version__ = "0.1.0"
__all__ = ['run_checks', 'check_gpu_memory']

# llama_env_checker/gpu_utils.py
import torch
import nvidia_sml_py3 as nvml
from typing import List, Dict, Tuple

def check_gpu_memory() -> List[Dict[str, float]]:
    """Check available GPU memory across all devices."""
    gpu_info = []
    
    try:
        nvml.nvmlInit()
        device_count = nvml.nvmlDeviceGetCount()
        
        for i in range(device_count):
            handle = nvml.nvmlDeviceGetHandleByIndex(i)
            info = nvml.nvmlDeviceGetMemoryInfo(handle)
            
            gpu_info.append({
                'device_id': i,
                'total_memory': info.total / (1024**3),  # Convert to GB
                'free_memory': info.free / (1024**3),
                'used_memory': info.used / (1024**3)
            })
            
    except Exception as e:
        print(f"Error checking GPU memory: {e}")
        
    finally:
        try:
            nvml.nvmlShutdown()
        except:
            pass
            
    return gpu_info

def check_cuda_availability() -> Tuple[bool, str]:
    """Check CUDA availability and version."""
    if not torch.cuda.is_available():
        return False, "CUDA is not available"
        
    return True, f"CUDA {torch.version.cuda} is available"

# llama_env_checker/checker.py
import subprocess
import json
import os
from typing import Dict, List, Tuple
from .gpu_utils import check_gpu_memory, check_cuda_availability

class LlamaEnvironmentChecker:
    def __init__(self):
        self.results = {
            'docker': [],
            'conda': {},
            'gpu': [],
            'env_vars': {},
            'cuda': {}
        }

    def check_docker_images(self) -> List[str]:
        """Check for Llama Stack related Docker images."""
        try:
            result = subprocess.run(
                ['docker', 'images', '--format', '{{.Repository}}:{{.Tag}}'],
                capture_output=True, text=True, check=True
            )
            images = result.stdout.strip().split('\n')
            self.results['docker'] = [img for img in images if 'llama' in img.lower()]
            return self.results['docker']
        except Exception:
            return []

    def check_conda_envs(self) -> Dict[str, List[str]]:
        """Check Conda environments for Llama Stack packages."""
        llama_packages = {
            'llama_stack',
            'llama_stack_client'
        }
        
        try:
            result = subprocess.run(
                ['conda', 'env', 'list', '--json'],
                capture_output=True, text=True, check=True
            )
            envs = json.loads(result.stdout)['envs']
            
            for env_path in envs:
                env_name = os.path.basename(env_path) or 'base'
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
                        self.results['conda'][env_name] = found_packages
                        
                except subprocess.CalledProcessError:
                    continue
                    
        except Exception:
            pass
            
        return self.results['conda']

    def check_environment_variables(self) -> Dict[str, Tuple[bool, str]]:
        """Check required environment variables."""
        env_vars = {
            'LLAMA_CHECKPOINT_DIR': os.getenv('LLAMA_CHECKPOINT_DIR'),
            'CUDA_VISIBLE_DEVICES': os.getenv('CUDA_VISIBLE_DEVICES')
        }
        
        for var, value in env_vars.items():
            if not value:
                self.results['env_vars'][var] = (False, f"{var} is not set")
                continue
                
            if var == 'LLAMA_CHECKPOINT_DIR' and not os.path.exists(value):
                self.results['env_vars'][var] = (False, f"{var} path does not exist: {value}")
                continue
                
            self.results['env_vars'][var] = (True, value)
            
        return self.results['env_vars']

    def run_all_checks(self) -> Dict:
        """Run all environment checks."""
        self.check_docker_images()
        self.check_conda_envs()
        self.check_environment_variables()
        self.results['gpu'] = check_gpu_memory()
        self.results['cuda'] = check_cuda_availability()
        return self.results

# llama_env_checker/startup.py
import argparse
import sys
from .checker import LlamaEnvironmentChecker

def format_results(results: dict) -> str:
    """Format check results into a readable string."""
    output = []
    
    output.append("\n=== Llama Stack Environment Check ===\n")
    
    # CUDA Status
    cuda_available, cuda_msg = results['cuda']
    output.append(f"CUDA Status: {cuda_msg}")
    
    # GPU Information
    output.append("\nGPU Status:")
    for gpu in results['gpu']:
        output.append(f"  Device {gpu['device_id']}:")
        output.append(f"    Total Memory: {gpu['total_memory']:.2f} GB")
        output.append(f"    Free Memory:  {gpu['free_memory']:.2f} GB")
        output.append(f"    Used Memory:  {gpu['used_memory']:.2f} GB")
    
    # Docker Images
    output.append("\nDocker Images:")
    if results['docker']:
        for img in results['docker']:
            output.append(f"  - {img}")
    else:
        output.append("  No Llama Stack Docker images found")
    
    # Conda Environments
    output.append("\nConda Environments:")
    if results['conda']:
        for env_name, packages in results['conda'].items():
            output.append(f"  - {env_name}: {', '.join(packages)}")
    else:
        output.append("  No Llama Stack packages found in Conda environments")
    
    # Environment Variables
    output.append("\nEnvironment Variables:")
    for var, (valid, message) in results['env_vars'].items():
        status = "✓" if valid else "✗"
        output.append(f"  {status} {var}: {message}")
    
    output.append("\n=== Check Complete ===")
    
    return "\n".join(output)

def main():
    parser = argparse.ArgumentParser(description='Llama Stack Environment Checker')
    parser.add_argument('--startup', action='store_true', 
                      help='Run in startup mode (exits on failure)')
    parser.add_argument('--json', action='store_true',
                      help='Output results in JSON format')
    args = parser.parse_args()
    
    checker = LlamaEnvironmentChecker()
    results = checker.run_all_checks()
    
    if args.json:
        print(json.dumps(results, indent=2))
        sys.exit(0)
    
    output = format_results(results)
    print(output)
    
    if args.startup:
        # Check for critical failures
        critical_failures = []
        
        if not results['cuda'][0]:  # CUDA not available
            critical_failures.append("CUDA not available")
            
        if not results['gpu']:  # No GPUs found
            critical_failures.append("No GPUs detected")
            
        if not results['env_vars'].get('LLAMA_CHECKPOINT_DIR', (False, ''))[0]:
            critical_failures.append("LLAMA_CHECKPOINT_DIR not properly set")
        
        if critical_failures:
            print("\nCritical failures detected:")
            for failure in critical_failures:
                print(f"  - {failure}")
            sys.exit(1)
    
if __name__ == "__main__":
    main()
