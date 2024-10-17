#!/bin/bash

# Get interface name as argument, default to eth0
interface="${1:-eth0}"

# Function to check if an IP address is private.  Improved regex.
is_private_ip() {
  ip="$1"
  [[ "$ip" =~ ^10\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]] || \
  [[ "$ip" =~ ^172\.(1[6-9]|2[0-9]|3[0-1])\.[0-9]{1,3}\.[0-9]{1,3}$ ]] || \
  [[ "$ip" =~ ^192\.168\.[0-9]{1,3}\.[0-9]{1,3}$ ]]
}

# Check if the interface exists and is UP
check_interface() {
  local interface="$1"
  if ! ip link show dev "$interface" &> /dev/null; then
    echo "Error: Interface '$interface' not found."
    return 1
  fi
  if ! ip link show dev "$interface" | grep "state UP"; then
    echo "Warning: Interface '$interface' is DOWN. Skipping IP address retrieval."
    return 1
  fi
  return 0
}


# Check Chrome OS interface
if ! check_interface "$interface"; then
  exit 1
fi

# Get Chrome OS IP address.  Add debugging output
echo "ip -4 addr show dev \"$interface\" output:"
ip -4 addr show dev "$interface"
chromeos_ip=$(ip -4 addr show dev "$interface" | grep "inet\b" | grep -v 127.0.0.1 | awk '{print $2}' | cut -d/ -f1)

if [ -z "$chromeos_ip" ]; then
  echo "Error: Could not determine Chrome OS IP address for interface '$interface'."
  exit 1
fi

echo "Chrome OS IP Address: $chromeos_ip"

# Get Linux VM IP address.  Assume a different interface for the VM (e.g., docker0)
vm_interface="docker0" # Change this if your VM uses a different interface

# Check if the VM interface exists and is UP
if ! check_interface "$vm_interface"; then
  echo "Warning: Linux VM IP address check skipped because interface '$vm_interface' is not found or is DOWN."
else
  # Add debugging output
  echo "ip -4 addr show dev \"$vm_interface\" output:"
  ip -4 addr show dev "$vm_interface"
  linux_ip=$(ip -4 addr show dev "$vm_interface" | grep "inet\b" | grep -v 127.0.0.1 | awk '{print $2}' | cut -d/ -f1)

  if [ -z "$linux_ip" ] || ! is_private_ip "$linux_ip"; then
    echo "Warning: Could not determine Linux VM IP address for interface '$vm_interface'."
  else
    echo "Linux VM IP Address: $linux_ip"
  fi
fi

# Describe the interaction (general information)
echo ""
echo "Interaction between Chrome OS and Linux VM:"
echo "The Linux VM runs in a container, isolated from the Chrome OS network. They communicate through a virtual network bridge created by Chrome OS. Chrome OS manages network access for the VM, assigning it an IP address on the virtual network. The VM can access the internet through this virtual network, and potentially communicate with Chrome OS using network protocols (e.g., SSH, if enabled)."
echo "Note: The Linux VM's IP address is typically only accessible from within the VM itself or from other VMs on the same virtual network. It's not directly routable on the external network."
