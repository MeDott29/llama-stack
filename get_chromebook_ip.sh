#!/bin/bash

# Get Chrome OS IP address.
chromeos_ip=$(ip -4 addr show | grep "inet\b" | grep -v 127.0.0.1 | awk '{print $2}' | cut -d/ -f1)

if [ -z "$chromeos_ip" ]; then
  echo "Error: Could not determine Chrome OS IP address. Check your network configuration."
  exit 1
fi

echo "Chrome OS IP Address: $chromeos_ip"

# Get Linux VM IP address.
linux_ip=$(ip -4 addr show | grep "inet\b" | grep -v 127.0.0.1 | awk '{print $2}' | cut -d/ -f1)

if [ -z "$linux_ip" ]; then
  echo "Warning: Could not determine Linux VM IP address. Check your Linux VM network configuration."
else
  echo "Linux VM IP Address: $linux_ip"
fi

# Describe the interaction (general information)
echo ""
echo "Interaction between Chrome OS and Linux VM:"
echo "The Linux VM runs in a container, isolated from the Chrome OS network. They communicate through a virtual network bridge created by Chrome OS. Chrome OS manages network access for the VM, assigning it an IP address on the virtual network. The VM can access the internet through this virtual network, and potentially communicate with Chrome OS using network protocols (e.g., SSH, if enabled)."
echo "Note: The Linux VM's IP address is typically only accessible from within the VM itself or from other VMs on the same virtual network. It's not directly routable on the external network."
