import bluetooth
import os


def ensure_bluetooth_on_and_visible():
    print("Ensure your Bluetooth is turned on and visible.")


def prompt_save_path(default_filename, gui_callback=None):
    """
    Prompt for save path, with optional GUI callback for directory selection
    gui_callback should return the full file path or None if cancelled
    """
    if gui_callback:
        return gui_callback(default_filename)
    
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


def receive_file(save_path, client_sock, file_size, progress_callback=None):
    """
    Receive file with optional progress callback
    progress_callback(bytes_received, total_size) if provided
    """
    try:
        with open(save_path, 'wb') as f:
            bytes_received = 0
            while bytes_received < file_size:
                data = client_sock.recv(1024)
                if not data:
                    break
                f.write(data)
                bytes_received += len(data)
                
                if progress_callback:
                    progress_callback(bytes_received, file_size)
                    
        print(f"File saved to: {save_path}")
        return True
    except Exception as e:
        print(f"Error saving file: {e}")
        return False


def start_receiver_blocking(gui_callback=None, progress_callback=None, log_callback=None):
    """
    Start receiver in blocking mode
    gui_callback: function(filename) -> save_path or None
    progress_callback: function(bytes_received, total_size)
    log_callback: function(message)
    Returns: True if successful, False otherwise
    """
    def log(msg):
        if log_callback:
            log_callback(msg)
        else:
            print(msg)
    
    ensure_bluetooth_on_and_visible()

    server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
    server_sock.bind(("", bluetooth.PORT_ANY))
    server_sock.listen(1)

    port = server_sock.getsockname()[1]
    bluetooth.advertise_service(server_sock, "BtFileReceiver",
                                service_classes=[bluetooth.SERIAL_PORT_CLASS],
                                profiles=[bluetooth.SERIAL_PORT_PROFILE])

    log(f"Waiting for connection on RFCOMM channel {port}...")

    try:
        client_sock, client_info = server_sock.accept()
        log(f"Connected to {client_info}")

        metadata = client_sock.recv(1024).decode()
        filename, file_size = metadata.split("::")
        file_size = int(file_size)

        log(f"Incoming file: {filename} ({file_size} bytes)")
        save_path = prompt_save_path(filename, gui_callback)
        
        if not save_path:
            log("File save cancelled")
            return False

        success = receive_file(save_path, client_sock, file_size, progress_callback)

        client_sock.close()
        server_sock.close()
        return success
    except Exception as e:
        log(f"Receiver error: {e}")
        return False


def start_receiver():
    """Original CLI function - preserved for backward compatibility"""
    return start_receiver_blocking()


def main():
    start_receiver()


if __name__ == '__main__':
    main()