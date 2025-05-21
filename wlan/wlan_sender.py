import os
import socket
import time

from .ipReceiver import get_devices_by_model, format_system_info

PORT = 54321  # Arbitrary port for file transfer

def flatten_devices_by_index(models):
    """Flatten the devices into a numbered list with references"""
    device_list = []
    for model in sorted(models):
        for device in models[model]:
            device_list.append(device)
    return device_list

def select_device(devices):
    """Prompt user to select a device by index"""
    while True:
        try:
            choice = input("Enter the number of the device to send to (or press Enter to refresh): ").strip()
            if choice == "":
                return None  # Trigger refresh
            index = int(choice) - 1
            if 0 <= index < len(devices):
                return devices[index]
            else:
                print("Invalid number. Try again.")
        except ValueError:
            print("Please enter a valid number.")

def send_file(ip, file_path, progress_callback=None, log_callback=None):
    """
    Send a file to the selected IP over TCP
    progress_callback: function(bytes_sent, total_size)
    log_callback: function(message)
    Returns: True if successful, False otherwise
    """
    def log(msg):
        if log_callback:
            log_callback(msg)
        else:
            print(msg)
    
    try:
        filesize = os.path.getsize(file_path)
        filename = os.path.basename(file_path)

        log(f"Connecting to {ip}:{PORT}...")
        with socket.create_connection((ip, PORT), timeout=45) as sock:
            log("Connected. Sending metadata...")
            sock.sendall(filename.encode() + b"\n")

            with open(file_path, "rb") as f:
                log(f"Sending file: {filename} ({filesize} bytes)...")
                bytes_sent = 0
                last_sent_time = time.time()
                
                while chunk := f.read(4096):
                    try:
                        sock.sendall(chunk)
                        bytes_sent += len(chunk)
                        last_sent_time = time.time()
                        
                        if progress_callback:
                            progress_callback(bytes_sent, filesize)
                            
                    except socket.timeout:
                        if time.time() - last_sent_time > 30:
                            log("No data sent for 30 seconds. Closing connection.")
                            return False
                        else:
                            log("Still sending data, hang tight...")
                            continue

        log("File sent successfully.")
        return True
    except Exception as e:
        log(f"Error sending file: {e}")
        return False


def send_file_to_device(device_ip, file_path, progress_callback=None, log_callback=None):
    """
    Wrapper function for UI - sends file to specific device IP
    """
    if not os.path.isfile(file_path):
        if log_callback:
            log_callback("File not found")
        return False
    
    return send_file(device_ip, file_path, progress_callback, log_callback)


def get_available_devices(timeout=2):
    """
    Get list of available devices for UI
    Returns: list of device dictionaries with 'name', 'ip', 'mac', 'model' keys
    """
    models = get_devices_by_model(timeout=timeout)
    return flatten_devices_by_index(models)


def main():
    while True:
        print("\nScanning for devices (2s)...")
        models = get_devices_by_model(timeout=2)
        devices = flatten_devices_by_index(models)

        if not devices:
            print("No devices found.")
            continue

        print("Available devices:")
        print(format_system_info(models))

        selected = select_device(devices)
        if selected is None:
            continue  # Refresh list

        print(f"Selected: {selected['name']} ({selected['ip']})")
        file_path = input("Enter path to file you wish to send: ").strip()

        if not os.path.isfile(file_path):
            print("Invalid file path. Exiting.")
            return

        send_file(selected["ip"], file_path)
        return  # Done after sending

if __name__ == "__main__":
    main()