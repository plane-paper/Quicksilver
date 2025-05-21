import socket
import threading
import os

from . import ipBroadcast

def run_broadcast():
    print("[Broadcast] Starting broadcast loop...")
    try:
        ipBroadcast.main()
    except Exception as e:
        print(f"[Broadcast] Error: {e}")


def receive_file_blocking(host='0.0.0.0', port=54321, gui_callback=None, log_callback=None, stop_flag=None):
    """
    Receive file in blocking mode with callbacks for GUI integration
    gui_callback: function(filename) -> save_path or None
    log_callback: function(message)
    stop_flag: threading.Event or similar object with is_set() method
    Returns: True if successful, False otherwise
    """
    def log(msg):
        if log_callback:
            log_callback(msg)
        else:
            print(f"[WLAN Receiver] {msg}")
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(1)
    server_socket.settimeout(1)  # Allow checking stop_flag
    
    log(f"Listening for incoming file on {host}:{port}...")

    while not (stop_flag and stop_flag.is_set()):
        try:
            conn, addr = server_socket.accept()
            log(f"Connection established from {addr[0]}")

            try:
                # Receive the filename
                filename = conn.recv(1024).decode().strip()
                if not filename:
                    log("Failed to receive filename.")
                    conn.close()
                    continue

                log(f"Incoming file: {filename}")
                
                # Get save path
                if gui_callback:
                    save_path = gui_callback(filename)
                    if not save_path:
                        log("File save cancelled")
                        conn.close()
                        continue
                else:
                    # CLI mode
                    while True:
                        save_path = input("Where should I save this file? (Enter full path): ").strip()
                        if os.path.isdir(save_path):
                            save_path = os.path.join(save_path, filename)
                            break
                        else:
                            print(f"[WLAN Receiver] Invalid directory: {save_path}. Please enter a valid directory.")
                            continue

                # Receive the file
                while True:
                    try:
                        with open(save_path, 'wb') as f:
                            log(f"Saving to {save_path}")
                            while not (stop_flag and stop_flag.is_set()):
                                try:
                                    data = conn.recv(4096)
                                    if not data:
                                        break
                                    f.write(data)
                                except socket.timeout:
                                    continue
                        log("File received successfully.")
                        server_socket.close()
                        return True
                    except PermissionError:
                        if gui_callback:
                            log(f"Permission denied for {save_path}")
                            save_path = gui_callback(filename)
                            if not save_path:
                                break
                        else:
                            log(f"Permission denied for {save_path}. Please choose a different path.")
                            save_path = input("Where should I save this file? (Enter full path): ").strip()
                            if os.path.isdir(save_path):
                                save_path = os.path.join(save_path, filename)
                    except Exception as e:
                        log(f"Error saving file: {e}")
                        break
            finally:
                conn.close()
                
        except socket.timeout:
            continue
        except Exception as e:
            if not (stop_flag and stop_flag.is_set()):
                log(f"Socket error: {e}")
    
    server_socket.close()
    return False


def receive_file(host='0.0.0.0', port=54321):
    """Original CLI function"""
    return receive_file_blocking(host, port)


def start_receiver_with_broadcast(gui_callback=None, log_callback=None, stop_flag=None):
    """
    Start receiver with background broadcasting
    """
    def log(msg):
        if log_callback:
            log_callback(msg)
        else:
            print(f"[Main] {msg}")
    
    log("Starting broadcast and receiver...")
    
    # Start broadcasting in a separate daemon thread
    broadcast_thread = threading.Thread(target=run_broadcast, daemon=True)
    broadcast_thread.start()
    
    # Start the receiver (blocks until a file is received or stopped)
    return receive_file_blocking('0.0.0.0', 54321, gui_callback, log_callback, stop_flag)


def main():
    start_receiver_with_broadcast()


if __name__ == '__main__':
    main()