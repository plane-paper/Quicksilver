import bluetooth
import os


def ensure_bluetooth_on_and_visible():
    print("Ensure your Bluetooth is turned on and visible.")


def prompt_save_path(default_filename):
    while True:
        save_path = input(f"Enter path to save '{default_filename}': ").strip('"')
        if not save_path:
            print("Path cannot be empty.")
            continue
        directory = os.path.dirname(save_path) or "."
        if not os.path.exists(directory):
            print("Directory does not exist.")
            continue
        return save_path


def receive_file(save_path, client_sock, file_size):
    try:
        with open(save_path, 'wb') as f:
            bytes_received = 0
            while bytes_received < file_size:
                data = client_sock.recv(1024)
                if not data:
                    break
                f.write(data)
                bytes_received += len(data)
        print(f"File saved to: {save_path}")
    except Exception as e:
        print(f"Error saving file: {e}")


def start_receiver():
    ensure_bluetooth_on_and_visible()

    server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
    server_sock.bind(("", bluetooth.PORT_ANY))
    server_sock.listen(1)

    port = server_sock.getsockname()[1]
    bluetooth.advertise_service(server_sock, "BtFileReceiver",
                                service_classes=[bluetooth.SERIAL_PORT_CLASS],
                                profiles=[bluetooth.SERIAL_PORT_PROFILE])

    print(f"📡 Waiting for connection on RFCOMM channel {port}...")

    try:
        client_sock, client_info = server_sock.accept()
        print(f"🔗 Connected to {client_info}")

        metadata = client_sock.recv(1024).decode()
        filename, file_size = metadata.split("::")
        file_size = int(file_size)

        print(f"📥 Incoming file: {filename} ({file_size} bytes)")
        save_path = prompt_save_path(filename)

        receive_file(save_path, client_sock, file_size)

        client_sock.close()
        server_sock.close()
    except Exception as e:
        print(f"Receiver error: {e}")


start_receiver()
