import bluetooth
import os


def ensure_bluetooth_on():
    print("Make sure Bluetooth is turned on.")


def discover_devices():
    print("Scanning for Bluetooth devices...")
    devices = bluetooth.discover_devices(duration=8, lookup_names=True)
    for i, (addr, name) in enumerate(devices, start=1):
        print(f"{i}. {name} [{addr}]") # Debug only
    return devices


def choose_device(devices):
    while True:
        try:
            choice = int(input("Choose a device to send to (number): "))
            if 1 <= choice <= len(devices):
                return devices[choice - 1]
            print("Invalid number.")
        except ValueError:
            print("Enter a valid integer.")


def get_valid_file_path():
    while True:
        path = input("Enter the path to the file you want to send: ").strip('"')
        if os.path.isfile(path):
            return path
        print("File not found.")


def send_file(addr, file_path, progress_callback=None, log_callback=None):
    """
    Send file to Bluetooth device
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
        sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        port = 1  # RFCOMM default
        sock.connect((addr, port))

        file_size = os.path.getsize(file_path)
        filename = os.path.basename(file_path)
        metadata = f"{filename}::{file_size}"
        sock.send(metadata.encode())

        with open(file_path, 'rb') as f:
            log(f"Sending '{filename}' ({file_size} bytes)...")
            bytes_sent = 0
            while True:
                chunk = f.read(1024)
                if not chunk:
                    break
                sock.send(chunk)
                bytes_sent += len(chunk)
                
                if progress_callback:
                    progress_callback(bytes_sent, file_size)

        sock.close()
        log("File sent successfully.")
        return True
    except Exception as e:
        log(f"Send error: {e}")
        return False


def send_file_to_device(device_addr, file_path, progress_callback=None, log_callback=None):
    """
    Wrapper function for UI - sends file to specific device address
    """
    if not os.path.isfile(file_path):
        if log_callback:
            log_callback("File not found")
        return False
    
    return send_file(device_addr, file_path, progress_callback, log_callback)


def main():
    ensure_bluetooth_on()
    devices = discover_devices()
    if devices:
        addr, name = choose_device(devices)
        file_path = get_valid_file_path()
        send_file(addr, file_path)


if __name__ == '__main__':
    main()