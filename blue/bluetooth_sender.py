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


def send_file(addr, file_path):
    try:
        sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        port = 1  # RFCOMM default
        sock.connect((addr, port))

        file_size = os.path.getsize(file_path)
        filename = os.path.basename(file_path)
        metadata = f"{filename}::{file_size}"
        sock.send(metadata.encode())

        with open(file_path, 'rb') as f:
            print(f"Sending '{filename}' ({file_size} bytes)...")
            while True:
                chunk = f.read(1024)
                if not chunk:
                    break
                sock.send(chunk)

        sock.close()
        print("File sent successfully.")
    except Exception as e:
        print(f"Send error: {e}")


def main():
    ensure_bluetooth_on()
    devices = discover_devices()
    if devices:
        addr, name = choose_device(devices)
        file_path = get_valid_file_path()
        send_file(addr, file_path)

if __name__ == '__main__':
    main()