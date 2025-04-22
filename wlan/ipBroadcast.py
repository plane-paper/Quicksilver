import socket
import time
import os
import platform
import sys
import ipaddress
import json
import re

def is_valid_json(s):
    try:
        json.loads(s)
        return True
    except json.JSONDecodeError:
        return False

def extract_ip(message):
    try:
        system_info = json.loads(message)  
        return system_info.get("ip")  
    except json.JSONDecodeError:
        print("Error: Invalid JSON format in message.")
        return None

# Basically useless unless the user wants to run the script on startup and manually configure it.
def auto_start():
    if platform.system() == "Windows":
        print("Setting up auto-start on Windows...")
        startup_path = os.path.join(os.getenv('APPDATA'), 'Microsoft\\Windows\\Start Menu\\Programs\\Startup')
        script_path = os.path.abspath(sys.argv[0])  # Get current script path
        symlink_path = os.path.join(startup_path, 'broadcast_program.lnk')

        # Create a shortcut or symlink in the startup folder
        if not os.path.exists(symlink_path):
            os.symlink(script_path, symlink_path)
            print(f"Script added to startup: {symlink_path}")
        else:
            print("Script is already in the startup folder.")

# Function to get system details for all network interfaces
def get_all_system_info():
    system_info_list = []
    
    # Get PC name
    pc_name = socket.gethostname()
    
    # Get model (Hardcoded Windows for now)
    model = "Windows"
    
    # Retrieve all network interfaces using socket
    interfaces = os.popen("ipconfig /all").read().split("\n")
    ip_address = None
    mac_address = None

    for line in interfaces:
        # Look for lines that contain "IPv4" addresses
        if "IPv4" in line and ("192.168" in line or "10" in line or "172" in line):
            # Use regex to extract just the IP address, ignoring the "Preferred" or other parts
            match = re.match(r"^\s*IPv4 Address[^\:]*:\s*([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)", line)
            if match:
                ip_address = match.group(1)  # Get the IP address
        if "Physical" in line:
            mac_address = line.split(":")[1].strip()

        if ip_address and mac_address:
            system_info_list.append({
                'name': pc_name,
                'model': model,
                'ip': ip_address,
                'mac': mac_address
            })
            ip_address = None  # Reset for next adapter
            mac_address = None  # Reset for next adapter
    
    return system_info_list


def get_broadcast_address(target_ip):
    # Loop through network interfaces and calculate broadcast address
    for interface in os.popen("ipconfig /all").read().split("\n"):
        if "IPv4" in interface and target_ip in interface:
            netmask_line = next((line for line in os.popen("ipconfig /all").read().split("\n") if "Subnet Mask" in line), None)
            if netmask_line:
                netmask = netmask_line.split(":")[1].strip()
                ip_network = ipaddress.IPv4Network(f"{target_ip}/{netmask}", strict=False)
                return str(ip_network.broadcast_address)
    return None

# Broadcasting the message
def broadcast_message(message):
    target_ip = extract_ip(message)
    if not target_ip:
        print("Error: No valid IP address found in message.")
        return

    #print(f"Broadcasting message via interface with IP: {target_ip}...")

    broadcast_ip = get_broadcast_address(target_ip)
    if not broadcast_ip:
        print(f"Error: No matching interface found for IP {target_ip}.")
        return

    port = 12345

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    try:
        sock.sendto(message.encode(), (broadcast_ip, port))
        #print(f"Message broadcasted successfully to {broadcast_ip}.")
    except Exception as e:
        print(f"Failed to broadcast message: {e}")
    finally:
        sock.close()

# Main function to run the program
def main():
    print("Starting the program...")

    # Infinite loop to repeatedly broadcast system information
    while True:
        # Get system info for all network adapters
        system_info_list = get_all_system_info()

        # If there are no valid interfaces to broadcast
        if not system_info_list:
            print("No valid network adapters found.")
            #break  # Exit the loop if no valid adapters found
        fuck = False
        # Broadcast the information for each network adapter separately
        for system_info in system_info_list:
            message = json.dumps(system_info, indent=4)
            if not is_valid_json(message):
                fuck = True
            broadcast_message(message)
              # Optional delay between messages if needed
        if fuck:
            print("Message format is not JSON. Exiting.")
            break
        # Wait for a while before broadcasting again
        time.sleep(2)  # 2 seconds delay between each full round of broadcasts

    # Auto start
    #auto_start() # Uncomment to enable auto-start

if __name__ == "__main__":
    # Run the main function
    main()
