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

def auto_start():
    if platform.system() == "Windows":
        print("Setting up auto-start on Windows...")
        startup_path = os.path.join(os.getenv('APPDATA'), 'Microsoft\\Windows\\Start Menu\\Programs\\Startup')
        script_path = os.path.abspath(sys.argv[0])
        symlink_path = os.path.join(startup_path, 'broadcast_program.lnk')

        if not os.path.exists(symlink_path):
            os.symlink(script_path, symlink_path)
            print(f"Script added to startup: {symlink_path}")
        else:
            print("Script is already in the startup folder.")

def get_all_system_info():
    system_info_list = []
    
    # Get PC name
    pc_name = socket.gethostname()
    model = "Windows"
    
    try:
        # Get ipconfig output
        ipconfig_output = os.popen("ipconfig /all").read()
        print("DEBUG: ipconfig output length:", len(ipconfig_output))  # Debug line
        
        # Split into sections by adapter
        sections = re.split(r'\n(?=\w)', ipconfig_output)
        
        for section in sections:
            lines = section.strip().split('\n')
            if not lines:
                continue
                
            ip_address = None
            mac_address = None
            
            # Look for IP and MAC in this section
            for line in lines:
                line = line.strip()
                
                # More flexible IPv4 matching - support both English and Chinese
                # English: "IPv4 Address" Chinese: "IPv4 地址"
                if ("IPv4" in line and ("Address" in line or "地址" in line)) or "IP 地址" in line:
                    # Extract IP using regex - handle different formats
                    ip_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', line)
                    if ip_match:
                        potential_ip = ip_match.group(1)
                        # Check if it's a private IP
                        if (potential_ip.startswith('192.168.') or 
                            potential_ip.startswith('10.') or 
                            potential_ip.startswith('172.')):
                            ip_address = potential_ip
                            print(f"DEBUG: Found IP: {ip_address}")  # Debug line
                
                # Look for MAC address - support both English and Chinese
                # English: "Physical Address" Chinese: "物理地址"
                if "Physical Address" in line or "物理地址" in line:
                    mac_match = re.search(r'([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}', line)
                    if mac_match:
                        mac_address = mac_match.group(0)
                        print(f"DEBUG: Found MAC: {mac_address}")  # Debug line
            
            # If we found both IP and MAC for this adapter, add it
            if ip_address and mac_address:
                system_info_list.append({
                    'name': pc_name,
                    'model': model,
                    'ip': ip_address,
                    'mac': mac_address
                })
                print(f"DEBUG: Added adapter - IP: {ip_address}, MAC: {mac_address}")
    
    except Exception as e:
        print(f"DEBUG: Error in get_all_system_info: {e}")
    
    print(f"DEBUG: Found {len(system_info_list)} valid adapters")
    return system_info_list

def get_all_system_info_english():
    """Try to get system info using English ipconfig command"""
    system_info_list = []
    pc_name = socket.gethostname()
    model = "Windows"
    
    try:
        # Try to force English output
        ipconfig_output = os.popen("chcp 437 && ipconfig /all").read()
        print("DEBUG: English ipconfig output length:", len(ipconfig_output))
        
        # Split into sections by adapter
        sections = re.split(r'\n(?=\w)', ipconfig_output)
        
        for section in sections:
            lines = section.strip().split('\n')
            if not lines:
                continue
                
            ip_address = None
            mac_address = None
            
            for line in lines:
                line = line.strip()
                
                # Look for IPv4 address
                if "IPv4" in line and "Address" in line:
                    ip_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', line)
                    if ip_match:
                        potential_ip = ip_match.group(1)
                        if (potential_ip.startswith('192.168.') or 
                            potential_ip.startswith('10.') or 
                            potential_ip.startswith('172.')):
                            ip_address = potential_ip
                            print(f"DEBUG: Found IP (English): {ip_address}")
                
                # Look for MAC address
                if "Physical Address" in line:
                    mac_match = re.search(r'([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}', line)
                    if mac_match:
                        mac_address = mac_match.group(0)
                        print(f"DEBUG: Found MAC (English): {mac_address}")
            
            if ip_address and mac_address:
                system_info_list.append({
                    'name': pc_name,
                    'model': model,
                    'ip': ip_address,
                    'mac': mac_address
                })
                print(f"DEBUG: Added adapter (English) - IP: {ip_address}, MAC: {mac_address}")
    
    except Exception as e:
        print(f"DEBUG: Error in get_all_system_info_english: {e}")
    
    return system_info_list

def get_all_system_info_alternative():
    """Alternative method using socket library"""
    system_info_list = []
    pc_name = socket.gethostname()
    model = "Windows"
    
    try:
        # Get local IP by connecting to a remote address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        
        print(f"DEBUG: Socket method found IP: {local_ip}")
        
        # For MAC address, we still need to parse ipconfig
        ipconfig_output = os.popen("ipconfig /all").read()
        mac_address = None
        
        # Find MAC address for the interface with our IP
        for line in ipconfig_output.split('\n'):
            if local_ip in line:
                # Look for Physical Address in nearby lines
                lines = ipconfig_output.split('\n')
                for i, search_line in enumerate(lines):
                    if local_ip in search_line:
                        # Check surrounding lines for MAC (support both English and Chinese)
                        for j in range(max(0, i-10), min(len(lines), i+10)):
                            if "Physical Address" in lines[j] or "物理地址" in lines[j]:
                                mac_match = re.search(r'([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}', lines[j])
                                if mac_match:
                                    mac_address = mac_match.group(0)
                                    break
                        break
        
        if local_ip and mac_address:
            system_info_list.append({
                'name': pc_name,
                'model': model,
                'ip': local_ip,
                'mac': mac_address
            })
        
    except Exception as e:
        print(f"DEBUG: Error in alternative method: {e}")
    
    return system_info_list

def get_broadcast_address(target_ip):
    try:
        ipconfig_output = os.popen("ipconfig /all").read()
        lines = ipconfig_output.split("\n")
        
        # Find the line with our target IP
        ip_line_index = -1
        for i, line in enumerate(lines):
            if target_ip in line and ("IPv4" in line or "IP 地址" in line):
                ip_line_index = i
                print(f"DEBUG: Found target IP line at index {i}: {line.strip()}")
                break
        
        if ip_line_index == -1:
            print(f"DEBUG: Could not find target IP {target_ip} in ipconfig output")
            return None
        
        # Look for subnet mask in nearby lines (both English and Chinese)
        netmask = None
        for j in range(ip_line_index, min(len(lines), ip_line_index + 10)):
            line = lines[j].strip()
            if "Subnet Mask" in line or "子网掩码" in line:
                # Extract the subnet mask
                if ":" in line:
                    netmask = line.split(":")[1].strip()
                    print(f"DEBUG: Found subnet mask: {netmask}")
                    break
        
        if not netmask:
            print("DEBUG: Could not find subnet mask, using default /24")
            # Default to /24 if we can't find the subnet mask
            netmask = "255.255.255.0"  
        
        # Calculate broadcast address
        ip_network = ipaddress.IPv4Network(f"{target_ip}/{netmask}", strict=False)
        broadcast_addr = str(ip_network.broadcast_address)
        print(f"DEBUG: Calculated broadcast address: {broadcast_addr}")
        return broadcast_addr
        
    except Exception as e:
        print(f"DEBUG: Error in get_broadcast_address: {e}")
        # Fallback: assume /24 network
        try:
            ip_parts = target_ip.split('.')
            broadcast_fallback = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.255"
            print(f"DEBUG: Using fallback broadcast address: {broadcast_fallback}")
            return broadcast_fallback
        except:
            return None

def broadcast_message(message):
    target_ip = extract_ip(message)
    if not target_ip:
        print("Error: No valid IP address found in message.")
        return

    broadcast_ip = get_broadcast_address(target_ip)
    if not broadcast_ip:
        print(f"Error: No matching interface found for IP {target_ip}.")
        return

    port = 12345

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    try:
        sock.sendto(message.encode(), (broadcast_ip, port))
        print(f"DEBUG: Broadcasted to {broadcast_ip}:{port}")
    except Exception as e:
        print(f"Failed to broadcast message: {e}")
    finally:
        sock.close()

def broadcast_system_info_once():
    try:
        system_info_list = get_all_system_info()
        
        # Try English version if first one fails
        if not system_info_list:
            print("DEBUG: First method failed, trying English version...")
            system_info_list = get_all_system_info_english()
        
        # Try alternative method if both fail
        if not system_info_list:
            print("DEBUG: English method failed, trying alternative...")
            system_info_list = get_all_system_info_alternative()
        
        if not system_info_list:
            return False
        
        for system_info in system_info_list:
            message = json.dumps(system_info, indent=4)
            if not is_valid_json(message):
                return False
            broadcast_message(message)
        
        return True
    except Exception as e:
        print(f"DEBUG: Exception in broadcast_system_info_once: {e}")
        return False

def start_broadcasting_loop(stop_flag=None):
    while not (stop_flag and stop_flag.is_set()):
        success = broadcast_system_info_once()
        if not success:
            break
        time.sleep(2)

def main():
    print("Starting the program...")

    while True:
        system_info_list = get_all_system_info()

        # Try English version if first fails
        if not system_info_list:
            print("DEBUG: Primary method failed, trying English version...")
            system_info_list = get_all_system_info_english()

        # Try alternative method if both fail
        if not system_info_list:
            print("DEBUG: English method failed, trying alternative...")
            system_info_list = get_all_system_info_alternative()

        if not system_info_list:
            print("No valid network adapters found.")
            print("DEBUG: This might be due to:")
            print("1. Different ipconfig output format")
            print("2. No private IP addresses (192.168.x.x, 10.x.x.x, 172.x.x.x)")
            print("3. Parsing issues")
            
            # Let's see what ipconfig actually returns
            print("\nDEBUG: Raw ipconfig output (first 1000 chars):")
            try:
                output = os.popen("ipconfig /all").read()
                print(repr(output[:1000]))
            except Exception as e:
                print(f"Error getting ipconfig: {e}")
            
            time.sleep(5)  # Wait before trying again instead of breaking
            continue

        json_invalid = False
        for system_info in system_info_list:
            message = json.dumps(system_info, indent=4)
            if not is_valid_json(message):
                json_invalid = True
            else:
                print(f"DEBUG: Broadcasting: {message}")
            broadcast_message(message)
        
        if json_invalid:
            print("Message format is not JSON. Exiting.")
            break
        
        time.sleep(2)

if __name__ == "__main__":
    main()