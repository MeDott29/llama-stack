#!/bin/bash

# Get Chrome OS IP address.  This is the most reliable method, but may need adjustments depending on your network configuration.
# Try a few different methods to find the IP address
chromeos_ip=$(ip route get 8.8.8.8 | awk '{print $NF;exit}') # Try using a public DNS server
if [ -z "$chromeos_ip" ]; then
  chromeos_ip=$(ip addr show | grep "inet\b" | grep -v 127.0.0.1 | awk '{print $2}' | cut -d/ -f1) # Try using ip addr
fi

if [ -z "$chromeos_ip" ]; then
  echo "Error: Could not determine Chrome OS IP address.  Check your network configuration."
  exit 1
fi

echo "Chrome OS IP Address: $chromeos_ip"

# Get Linux VM IP address. This is less reliable and may require adjustments.
# It assumes the Linux VM has network connectivity and a default route.  We'll try several methods.

# Try using ip route first (most likely to work)
linux_ip=$(ip route get 8.8.8.8 | awk '{print $NF;exit}')

# If that fails, try ifconfig (less likely to work, and might need sudo)
if [ -z "$linux_ip" ]; then
  linux_ip=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | cut -d: -f2 | head -n 1)
fi

# If still fails, try ip addr
if [ -z "$linux_ip" ]; then
  linux_ip=$(ip addr show | grep "inet\b" | grep -v 127.0.0.1 | awk '{print $2}' | cut -d/ -f1)
fi


if [ -z "$linux_ip" ]; then
  echo "Warning: Could not determine Linux VM IP address. Check your Linux VM network configuration."
else
  echo "Linux VM IP Address: $linux_ip"
fi


# Describe the interaction (general information)
echo ""
echo "Interaction between Chrome OS and Linux VM:"
echo "The Linux VM runs in a container, isolated from the Chrome OS network.  They communicate through a virtual network bridge created by Chrome OS.  Chrome OS manages network access for the VM, assigning it an IP address on the virtual network.  The VM can access the internet through this virtual network, and potentially communicate with Chrome OS using network protocols (e.g., SSH, if enabled)."
echo "Note:  The Linux VM's IP address is typically only accessible from within the VM itself or from other VMs on the same virtual network.  It's not directly routable on the external network."

