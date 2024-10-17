#!/bin/bash

# Function to list available interfaces, excluding loopback
list_interfaces() {
  ip link show | awk '/^[0-9]+: / {print $2}'
}

# Function to check if an IP address is private.  Improved regex.
is_private_ip() {
  ip="$1"
  [[ "$ip" =~ ^10\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]] || \
  [[ "$ip" =~ ^172\.(1[6-9]|2[0-9]|3[0-1])\.[0-9]{1,3}\.[0-9]{1,3}$ ]] || \
  [[ "$ip" =~ ^192\.168\.[0-9]{1,3}\.[0-9]{1,3}$ ]]
}

# Function to check and get IP for a given interface
check_and_get_ip() {
  local interface="$1"
  echo "Checking interface: $interface"

  #Check if interface exists and is up *before* attempting to get the IP address
  if ! ip link show dev "$interface" &> /dev/null; then
    echo "Error: Interface '$interface' not found."
    return
  fi
  if ! ip link show dev "$interface" | grep -q "state UP"; then
    echo "Warning: Interface '$interface' is DOWN. Skipping IP address retrieval."
    return
  fi

  # Remove trailing colon and @ifX suffix AFTER the interface check
  interface="${interface%%:*}" # Remove trailing colon
  interface="${interface//@*/}" #Remove @ and anything after it.

  ip -4 addr show dev "$interface"
  chromeos_ip=$(ip -4 addr show dev "$interface" | grep "inet\b" | grep -v 127.0.0.1 | awk '{print $2}' | cut -d/ -f1)

  if [ -z "$chromeos_ip" ]; then
    echo "Warning: Could not determine Chrome OS IP address for interface '$interface'."
    return
  fi

  echo "Chrome OS IP Address for interface '$interface': $chromeos_ip"
  echo ""
}


# Get interface name. If only one interface (excluding loopback) is found, use that. Otherwise, prompt the user with a list of available interfaces.
available_interfaces=$(list_interfaces)
if [[ $(echo "$available_interfaces" | wc -l) -eq 1 ]]; then
  interface=$(echo "$available_interfaces")
elif [[ $(echo "$available_interfaces" | wc -l) -eq 0 ]]; then
  echo "Error: No interfaces found."
  exit 1
else
  echo "Available interfaces:"
  i=1
  for interface in $available_interfaces; do
    echo "$i. $interface"
    i=$((i+1))
  done
  read -p "Enter the number of the interface for the Chrome OS connection (or press Enter to skip): " interface_num

  if [[ -z "$interface_num" ]]; then
    echo "No interface selected. Testing all interfaces..."
    for interface in $available_interfaces; do
      check_and_get_ip "$interface"
    done
    exit 0
  fi

  if [[ ! "$interface_num" =~ ^[0-9]+$ ]] || [[ "$interface_num" -gt "$i" ]] || [[ "$interface_num" -lt 1 ]]; then
    echo "Invalid interface number."
    exit 1
  fi

  interface=$(echo "$available_interfaces" | awk -v num="$interface_num" 'NR==num {print}')

  #Check if interface exists
  if ! ip link show dev "$interface" &> /dev/null; then
    echo "Error: Interface '$interface' not found."
    exit 1
  fi
fi


# Check Chrome OS interface (if a single interface was selected)
if [[ -n "$interface" ]]; then
  check_and_get_ip "$interface"
fi


# Get the VM's IP address on the local network.  This assumes the VM has a connection to the local network.
vm_ip=$(ip -4 addr show | grep "inet\b" | grep -v 127.0.0.1 | awk '{print $2}' | cut -d/ -f1)

if [ -z "$vm_ip" ]; then
  echo "Warning: Could not determine VM's IP address on the local network."
else
  echo "VM IP Address (Local Network): $vm_ip"
fi

# Describe the interaction (general information)
echo ""
echo "Interaction between Chrome OS and Linux VM:"
echo "The script is running inside the Linux VM. The VM is connected to the Chrome OS network via a virtual network interface.  The VM also has a separate connection to the local network, allowing it to communicate with other devices on that network. The Chrome OS IP address is obtained from the virtual network interface, while the VM's local network IP address is obtained separately."
echo "Note: The Chrome OS IP address is only accessible from within the VM or other devices on the same virtual network. The VM's local network IP address is accessible from other devices on the local network."
