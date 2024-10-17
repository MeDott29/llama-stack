#!/bin/bash

# Get interface name as argument, default to eth0 if only one interface is found, otherwise prompt the user.
if [[ $(ip link show | wc -l) -eq 2 ]]; then # Check if only one interface exists (excluding loopback)
  interface=$(ip link show | grep -oP '(?<=dev\s)\w+' | head -n 1)
else
  read -p "Enter the interface name for the Chrome OS connection (e.g., eth0): " interface
fi

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

# Get the VM's IP address on the local network.  This assumes the VM has a connection to the local network.
vm_ip=$(ip -4 addr show | grep "inet\b" | grep -v 127.0.0.1 | grep -v "$chromeos_ip" | awk '{print $2}' | cut -d/ -f1)

if [ -z "$vm_ip" ]; then
  echo "Warning: Could not determine VM's IP address on the local network."
else
  echo "VM IP Address (Local Network): $vm_ip"
fi

# Describe the interaction (general information)
echo ""
echo "Interaction between Chrome OS and Linux VM:"
echo "The script is running inside the Linux VM. The VM is connected to the Chrome OS network via a virtual network interface ($interface).  The VM also has a separate connection to the local network, allowing it to communicate with other devices on that network. The Chrome OS IP address is obtained from the virtual network interface, while the VM's local network IP address is obtained separately."
echo "Note: The Chrome OS IP address is only accessible from within the VM or other devices on the same virtual network. The VM's local network IP address is accessible from other devices on the local network."
