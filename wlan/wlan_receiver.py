import socket
import threading
import os

import ipBroadcast

def run_broadcast():
    print("[Broadcast] Starting broadcast loop...")
    try:
        ipBroadcast.main()
    except Exception as e:
        print(f"[Broadcast] Error: {e}")

def receive_file(host='0.0.0.0', port=54321):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(1)
    print(f"[WLAN Receiver] Listening for incoming file on {host}:{port}...")

    conn, addr = server_socket.accept()
    print(f"[WLAN Receiver] Connection established from {addr[0]}")

    # Receive the filename
    filename = conn.recv(1024).decode().strip()
    if not filename:
        print("[WLAN Receiver] Failed to receive filename.")
        conn.close()
        return

    # Prompt user for save path
    print(f"[WLAN Receiver] Incoming file: {filename}")
    while True:
        save_path = input("Where should I save this file? (Enter full path): ").strip()

        if os.path.isdir(save_path):
            save_path = os.path.join(save_path, filename)
            break
        else:
            print(f"[WLAN Receiver] Invalid directory: {save_path}. Please enter a valid directory.")
            continue

    while True:
        try:
            with open(save_path, 'wb') as f:
                print(f"[WLAN Receiver] Saving to {save_path}")
                while True:
                    data = conn.recv(4096)
                    if not data:
                        break
                    f.write(data)
            print("[WLAN Receiver] File received successfully.")
            break
        except PermissionError:
            print(f"[WLAN Receiver] Permission denied for {save_path}. Please choose a different path.")
            save_path = input("Where should I save this file? (Enter full path): ").strip()
            if os.path.isdir(save_path):
                save_path = os.path.join(save_path, filename)
        except Exception as e:
            print(f"[WLAN Receiver] Error saving file: {e}")
            break

    conn.close()
    server_socket.close()

def main():
    print("[Main] Starting broadcast and receiver...")
    # Start broadcasting in a separate daemon thread
    threading.Thread(target=run_broadcast, daemon=True).start()
    
    # Start the receiver loop (blocks until a file is received)
    receive_file()

if __name__ == '__main__':
    main()
