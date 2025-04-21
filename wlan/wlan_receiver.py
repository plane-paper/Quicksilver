import socket
import threading
import os

import ipBroadcast

def run_broadcast():
    # Just call the existing main() from ipBroadcast.py
    ipBroadcast.main()

def receive_file(host='0.0.0.0', port=54321):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(1)
    print(f"[Receiver] Listening for incoming file on {host}:{port}...")

    conn, addr = server_socket.accept()
    print(f"[Receiver] Connection established from {addr[0]}")

    # Receive the filename
    filename = conn.recv(1024).decode()
    if not filename:
        print("[Receiver] Failed to receive filename.")
        conn.close()
        return

    # Prompt user for save path
    print(f"[Receiver] Incoming file: {filename}")
    save_path = input("Where should I save this file? (Enter full path): ").strip()

    if os.path.isdir(save_path):
        save_path = os.path.join(save_path, filename)

    try:
        with open(save_path, 'wb') as f:
            print(f"[Receiver] Saving to {save_path}")
            while True:
                data = conn.recv(4096)
                if not data:
                    break
                f.write(data)
        print("[Receiver] File received successfully.")
    except Exception as e:
        print(f"[Receiver] Error saving file: {e}")

    conn.close()
    server_socket.close()

def main():
    # Start broadcasting in a separate daemon thread
    threading.Thread(target=run_broadcast, daemon=True).start()
    
    # Start the receiver loop (blocks until a file is received)
    receive_file()

if __name__ == '__main__':
    main()
