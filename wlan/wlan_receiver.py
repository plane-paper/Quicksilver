import socket
import threading
import os
import errno
import time

from . import ipBroadcast

def run_broadcast():
    print("[Broadcast] Starting broadcast loop...")
    try:
        ipBroadcast.main()
    except Exception as e:
        print(f"[Broadcast] Error: {e}")

def find_available_port(start_port=54321, max_attempts=10):
    """Find an available port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        try:
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            test_socket.bind(('0.0.0.0', port))
            test_socket.close()
            return port
        except OSError:
            continue
    return None

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
    
    # Try to find an available port if the default is in use
    original_port = port
    available_port = find_available_port(port)
    
    if available_port is None:
        log(f"Error: Cannot find an available port starting from {port}")
        return False
    
    if available_port != original_port:
        log(f"Port {original_port} is in use. Using port {available_port} instead.")
        port = available_port
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Additional socket options to handle various network conditions
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        
        try:
            server_socket.bind((host, port))
        except OSError as e:
            if e.errno == errno.EACCES or e.winerror == 10013:
                log(f"Permission denied when binding to port {port}. Try running as administrator or use a different port.")
                log("Common solutions:")
                log("1. Run the application as Administrator")
                log("2. Check if another application is using this port")
                log("3. Configure Windows Firewall to allow this application")
                log("4. Try a different port number")
                return False
            elif e.errno == errno.EADDRINUSE or e.winerror == 10048:
                log(f"Port {port} is already in use by another application")
                return False
            else:
                log(f"Failed to bind to {host}:{port} - Error: {e}")
                return False
        
        server_socket.listen(1)
        server_socket.settimeout(1)  # Allow checking stop_flag
        
        log(f"Listening for incoming file on {host}:{port}...")

        while not (stop_flag and stop_flag.is_set()):
            try:
                conn, addr = server_socket.accept()
                log(f"Connection established from {addr[0]}")

                try:
                    # Set a timeout for the connection
                    conn.settimeout(30)
                    
                    # Receive the filename
                    filename_data = conn.recv(1024)
                    if not filename_data:
                        log("Failed to receive filename.")
                        conn.close()
                        continue

                    filename = filename_data.decode().strip()
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
                    retry_count = 0
                    max_retries = 3
                    
                    while retry_count < max_retries:
                        try:
                            with open(save_path, 'wb') as f:
                                log(f"Saving to {save_path}")
                                bytes_received = 0
                                
                                while not (stop_flag and stop_flag.is_set()):
                                    try:
                                        data = conn.recv(4096)
                                        if not data:
                                            break
                                        f.write(data)
                                        bytes_received += len(data)
                                    except socket.timeout:
                                        # Check if we're still supposed to be running
                                        if stop_flag and stop_flag.is_set():
                                            break
                                        continue
                                    except ConnectionResetError:
                                        log("Connection was reset by sender")
                                        break
                                    except Exception as recv_error:
                                        log(f"Error receiving data: {recv_error}")
                                        break
                                        
                            log(f"File received successfully. Total bytes: {bytes_received}")
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
                            log(f"Error saving file (attempt {retry_count + 1}): {e}")
                            retry_count += 1
                            if retry_count < max_retries:
                                log(f"Retrying... ({retry_count + 1}/{max_retries})")
                                time.sleep(1)
                            else:
                                log("Max retries reached. File transfer failed.")
                                break
                    
                except socket.timeout:
                    log("Connection timed out while receiving file")
                except Exception as e:
                    log(f"Error during file transfer: {e}")
                finally:
                    try:
                        conn.close()
                    except:
                        pass
                        
            except socket.timeout:
                continue
            except Exception as e:
                if not (stop_flag and stop_flag.is_set()):
                    log(f"Socket error: {e}")
    
    except Exception as e:
        log(f"Fatal error in receiver: {e}")
    finally:
        try:
            server_socket.close()
        except:
            pass
    
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