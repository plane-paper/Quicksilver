import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import socket
import threading
import os
import time
import json

# Import WLAN modules
from wlan.ipReceiver import get_devices_by_model, format_system_info, format_time_ago
from wlan.wlan_sender import send_file as wlan_send_file
from wlan.ipBroadcast import get_all_system_info

# Import Bluetooth modules
from blue.bluetooth_sender import discover_devices, send_file as bt_send_file
from blue.bluetooth_receiver import ensure_bluetooth_on_and_visible

class FileTransferApp:
    def __init__(self, root):
        self.root = root
        self.root.title("File Transfer App")
        self.root.geometry("500x400")
        self.root.configure(padx=20, pady=20)
        
        self.sending = False
        self.receiving = False
        self.file_path = tk.StringVar()
        self.send_method = tk.StringVar(value="Wi-Fi")
        self.selected_device = None
        self.devices_list = []
        self.bt_devices = []
        
        self.create_notebook()
        
        # Start broadcasting in background
        self.broadcast_thread = threading.Thread(target=self.start_background_broadcast, daemon=True)
        self.broadcast_thread.start()
        
    def create_notebook(self):
        """Create a tabbed interface"""
        notebook = ttk.Notebook(self.root)
        notebook.pack(expand=True, fill="both")
        
        # Create tabs
        send_frame = ttk.Frame(notebook)
        receive_frame = ttk.Frame(notebook)
        
        notebook.add(send_frame, text="Send File")
        notebook.add(receive_frame, text="Receive File")
        
        # Build the UI for each tab
        self.build_send_ui(send_frame)
        self.build_receive_ui(receive_frame)
    
    def build_send_ui(self, parent):
        """Build the UI for sending files"""
        # File selection row
        ttk.Label(parent, text="File:").pack(anchor="w")
        file_frame = ttk.Frame(parent)
        file_frame.pack(fill="x", pady=(0, 10))
        
        file_entry = ttk.Entry(file_frame, textvariable=self.file_path)
        file_entry.pack(side="left", fill="x", expand=True)
        
        browse_button = ttk.Button(file_frame, text="Browse", command=self.browse_file)
        browse_button.pack(side="right", padx=(5, 0))
        
        # Send via options
        ttk.Label(parent, text="Send via:").pack(anchor="w")
        
        methods_frame = ttk.Frame(parent)
        methods_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Radiobutton(methods_frame, text="Wi-Fi", variable=self.send_method, 
                       value="Wi-Fi", command=self.refresh_devices).pack(side="left", padx=(0, 10))
        ttk.Radiobutton(methods_frame, text="Bluetooth", variable=self.send_method,
                       value="Bluetooth", command=self.refresh_devices).pack(side="left")
        
        refresh_btn = ttk.Button(methods_frame, text="Refresh", command=self.refresh_devices)
        refresh_btn.pack(side="right")
        
        # Computer selection
        ttk.Label(parent, text="Select a device:").pack(anchor="w", pady=(10, 0))
        
        self.device_listbox = tk.Listbox(parent, height=8, exportselection=False)
        self.device_listbox.pack(fill="both", expand=True, pady=(0, 10))
        self.device_listbox.bind("<<ListboxSelect>>", self.on_device_select)
        
        # Status frame
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill="x", pady=(0, 10))
        
        self.status_label = ttk.Label(status_frame, text="Ready")
        self.status_label.pack(side="left")
        
        self.progress_bar = ttk.Progressbar(status_frame, orient="horizontal", mode="indeterminate")
        
        # Send button
        self.send_button = ttk.Button(parent, text="Send", command=self.send_file)
        self.send_button.pack(pady=(10, 0))
        
        # Initially populate devices list
        self.refresh_devices()
    
    def build_receive_ui(self, parent):
        """Build the UI for receiving files"""
        # Information frame
        info_frame = ttk.LabelFrame(parent, text="Receiver Status")
        info_frame.pack(fill="x", pady=(0, 10))
        
        self.receive_method = tk.StringVar(value="Wi-Fi")
        ttk.Radiobutton(info_frame, text="Wi-Fi", variable=self.receive_method, 
                       value="Wi-Fi", command=self.toggle_receiver).pack(anchor="w")
        ttk.Radiobutton(info_frame, text="Bluetooth", variable=self.receive_method,
                       value="Bluetooth", command=self.toggle_receiver).pack(anchor="w")
        
        # Status indicators
        self.receiver_status = ttk.Label(info_frame, text="Receiver is OFF")
        self.receiver_status.pack(anchor="w", pady=5)
        
        self.receiver_info = ttk.Label(info_frame, text="")
        self.receiver_info.pack(anchor="w", pady=5)
        
        # Receive controls
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill="x", pady=(10, 0))
        
        self.start_receiver_btn = ttk.Button(control_frame, text="Start Receiver", command=self.start_receiver)
        self.start_receiver_btn.pack(side="left", padx=(0, 10))
        
        self.stop_receiver_btn = ttk.Button(control_frame, text="Stop Receiver", command=self.stop_receiver)
        self.stop_receiver_btn.pack(side="left")
        self.stop_receiver_btn.config(state="disabled")
        
        # Log frame
        log_frame = ttk.LabelFrame(parent, text="Receive Log")
        log_frame.pack(fill="both", expand=True, pady=(10, 0))
        
        self.log_text = tk.Text(log_frame, height=10, wrap="word")
        self.log_text.pack(fill="both", expand=True)
        
    def log(self, message):
        """Add a message to the log with timestamp"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.see("end")  # Scroll to the end
    
    def browse_file(self):
        """Open file browser to select a file"""
        file = filedialog.askopenfilename(title="Select a file")
        if file:
            self.file_path.set(file)
    
    def refresh_devices(self):
        """Refresh the list of available devices"""
        self.status_label.config(text="Scanning for devices...")
        self.devices_list = []
        self.device_listbox.delete(0, tk.END)
        
        # Show progress bar while scanning
        self.progress_bar.pack(side="right", fill="x", expand=True)
        self.progress_bar.start()
        
        # Run device discovery in a thread
        threading.Thread(target=self._refresh_devices_thread, daemon=True).start()
    
    def _refresh_devices_thread(self):
        """Background thread to discover devices"""
        method = self.send_method.get()
        
        if method == "Wi-Fi":
            # Get WLAN devices
            models = get_devices_by_model(timeout=2)
            self.devices_list = []
            
            for model in sorted(models.keys()):
                for device in models[model]:
                    display_text = f"{device['name']} [{device['ip']}] - {format_time_ago(device['last_seen'])}"
                    self.devices_list.append({
                        'display': display_text,
                        'ip': device['ip'],
                        'name': device['name'],
                        'mac': device['mac'],
                        'type': 'wifi'
                    })
        else:
            # Get Bluetooth devices
            bt_devices = discover_devices()
            self.devices_list = []
            
            for i, (addr, name) in enumerate(bt_devices):
                display_text = f"{name} [{addr}]"
                self.devices_list.append({
                    'display': display_text,
                    'addr': addr,
                    'name': name,
                    'type': 'bluetooth'
                })
        
        # Update UI in main thread
        self.root.after(0, self._update_device_listbox)
    
    def _update_device_listbox(self):
        """Update the device listbox with discovered devices"""
        self.device_listbox.delete(0, tk.END)
        
        if not self.devices_list:
            self.device_listbox.insert(tk.END, "No devices found")
            self.device_listbox.config(state="disabled")
        else:
            self.device_listbox.config(state="normal")
            for device in self.devices_list:
                self.device_listbox.insert(tk.END, device['display'])
        
        # Stop progress bar
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.status_label.config(text="Ready")
    
    def on_device_select(self, event):
        """Handle device selection from listbox"""
        selection = self.device_listbox.curselection()
        if not selection or not self.devices_list:
            self.selected_device = None
            return
        
        index = selection[0]
        if 0 <= index < len(self.devices_list):
            self.selected_device = self.devices_list[index]
            device_name = self.selected_device.get('name', 'Unknown')
            self.status_label.config(text=f"Selected: {device_name}")
    
    def send_file(self):
        """Initiate file sending process"""
        if self.sending:
            return
        
        # Validate inputs
        if not self.file_path.get():
            messagebox.showerror("Error", "Please select a file to send")
            return
        
        if not os.path.isfile(self.file_path.get()):
            messagebox.showerror("Error", "The selected file does not exist")
            return
        
        if not self.selected_device:
            messagebox.showerror("Error", "Please select a device to send to")
            return
        
        # Start sending
        self.sending = True
        self.send_button.config(state="disabled")
        self.status_label.config(text="Sending file...")
        self.progress_bar.pack(side="right", fill="x", expand=True)
        self.progress_bar.start()
        
        # Run the transfer in a background thread
        threading.Thread(target=self._send_file_thread, daemon=True).start()
    
    def _send_file_thread(self):
        """Background thread to handle file sending"""
        try:
            method = self.send_method.get()
            file_path = self.file_path.get()
            
            if method == "Wi-Fi" and self.selected_device['type'] == 'wifi':
                # Send via WLAN
                ip = self.selected_device['ip']
                self.root.after(0, lambda: self.status_label.config(text=f"Connecting to {ip}..."))
                wlan_send_file(ip, file_path)
            elif method == "Bluetooth" and self.selected_device['type'] == 'bluetooth':
                # Send via Bluetooth
                addr = self.selected_device['addr']
                self.root.after(0, lambda: self.status_label.config(text=f"Connecting to {addr}..."))
                bt_send_file(addr, file_path)
            else:
                self.root.after(0, lambda: messagebox.showerror("Error", "Selected device does not support this transfer method"))
                
            # Success
            self.root.after(0, lambda: messagebox.showinfo("Success", "File sent successfully"))
        except Exception as e:
            # Error
            self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to send file: {str(e)}"))
        finally:
            # Reset UI state
            self.root.after(0, self._reset_send_ui)
    
    def _reset_send_ui(self):
        """Reset UI after send operation"""
        self.sending = False
        self.send_button.config(state="normal")
        self.status_label.config(text="Ready")
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
    
    def start_background_broadcast(self):
        """Start broadcasting system info in background"""
        while True:
            try:
                # Only broadcast if we're not currently sending
                if not self.sending:
                    system_info_list = get_all_system_info()
                    for system_info in system_info_list:
                        message = json.dumps(system_info)
                        try:
                            # Call broadcast_message without referencing it directly
                            # since it's not properly defined in ipBroadcast.py
                            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                            broadcast_ip = self._calculate_broadcast_address(system_info['ip'])
                            if broadcast_ip:
                                sock.sendto(message.encode(), (broadcast_ip, 12345))
                            sock.close()
                        except Exception:
                            pass
            except Exception:
                # Silently ignore errors in background thread
                pass
            
            # Sleep for a while
            time.sleep(2)
    
    def _calculate_broadcast_address(self, ip):
        """Calculate broadcast address for an IP (simplified)"""
        # Simple method: assume /24 network
        parts = ip.split('.')
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.{parts[2]}.255"
        return None
    
    def toggle_receiver(self):
        """Toggle the receiver method"""
        # Stop any running receiver
        if self.receiving:
            self.stop_receiver()
    
    def start_receiver(self):
        """Start the receiver based on selected method"""
        if self.receiving:
            return
        
        method = self.receive_method.get()
        self.log(f"Starting {method} receiver...")
        
        self.receiving = True
        self.start_receiver_btn.config(state="disabled")
        self.stop_receiver_btn.config(state="normal")
        
        # Start receiver in background thread
        self.receiver_thread = threading.Thread(target=self._run_receiver, daemon=True)
        self.receiver_thread.start()
        
        # Update UI
        if method == "Wi-Fi":
            ip = self._get_local_ip()
            self.receiver_status.config(text="Wi-Fi Receiver is ACTIVE")
            self.receiver_info.config(text=f"Listening on {ip}:54321")
        else:
            self.receiver_status.config(text="Bluetooth Receiver is ACTIVE")
            self.receiver_info.config(text="Bluetooth device is discoverable")
    
    def stop_receiver(self):
        """Stop the active receiver"""
        if not self.receiving:
            return
        
        self.log("Stopping receiver...")
        self.receiving = False
        # The receiver thread will terminate on next iteration
        
        # Update UI
        self.start_receiver_btn.config(state="normal")
        self.stop_receiver_btn.config(state="disabled")
        self.receiver_status.config(text="Receiver is OFF")
        self.receiver_info.config(text="")

    def _run_receiver(self):
        """Run the appropriate receiver in a background thread"""
        method = self.receive_method.get()
        
        try:
            if method == "Wi-Fi":
                self._run_wlan_receiver()
            else:
                self._run_bluetooth_receiver()
        except Exception as e:
            self.log(f"Error in receiver: {e}")
        finally:
            # Reset UI if the thread exits for any reason
            if self.receiving:
                self.root.after(0, self.stop_receiver)
    
    def _run_wlan_receiver(self):
        """Run the WLAN receiver"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind(('0.0.0.0', 54321))
        server_socket.listen(1)
        server_socket.settimeout(1)  # Allow polling for stop flag
        
        self.log("WLAN receiver started, waiting for connections...")
        
        while self.receiving:
            try:
                conn, addr = server_socket.accept()
                self.log(f"Connection from {addr[0]}")
                
                # Receive filename
                try:
                    filename = conn.recv(1024).decode().strip()
                    if not filename:
                        self.log("Failed to receive filename")
                        conn.close()
                        continue
                        
                    self.log(f"Receiving file: {filename}")
                    
                    # Ask user for save location
                    save_dir = filedialog.askdirectory(title=f"Save '{filename}' to:")
                    if not save_dir:
                        self.log("File save canceled")
                        conn.close()
                        continue
                    
                    save_path = os.path.join(save_dir, filename)
                    
                    # Receive the file
                    with open(save_path, 'wb') as f:
                        while self.receiving:
                            try:
                                data = conn.recv(4096)
                                if not data:
                                    break
                                f.write(data)
                            except socket.timeout:
                                continue
                    
                    self.log(f"File saved to: {save_path}")
                except Exception as e:
                    self.log(f"Error receiving file: {e}")
                finally:
                    conn.close()
                    
            except socket.timeout:
                # This is just to check the receiving flag periodically
                continue
            except Exception as e:
                self.log(f"Socket error: {e}")
                time.sleep(1)  # Prevent CPU spike on repeated errors
        
        # Clean up
        try:
            server_socket.close()
        except:
            pass
    
    def _run_bluetooth_receiver(self):
        """Run the Bluetooth receiver"""
        import bluetooth  # Import here to prevent issues if bluetooth isn't available
        
        ensure_bluetooth_on_and_visible()
        self.log("Bluetooth receiver started, device is discoverable")
        
        server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        server_sock.bind(("", bluetooth.PORT_ANY))
        server_sock.listen(1)
        port = server_sock.getsockname()[1]
        
        # Advertise service
        bluetooth.advertise_service(
            server_sock, "BtFileReceiver",
            service_classes=[bluetooth.SERIAL_PORT_CLASS],
            profiles=[bluetooth.SERIAL_PORT_PROFILE]
        )
        
        self.log(f"Listening on RFCOMM channel {port}")
        server_sock.settimeout(1)  # Allow polling for stop flag
        
        while self.receiving:
            try:
                client_sock, client_info = server_sock.accept()
                self.log(f"Connection from {client_info}")
                
                try:
                    # Get file metadata
                    metadata = client_sock.recv(1024).decode()
                    filename, file_size = metadata.split("::")
                    file_size = int(file_size)
                    
                    self.log(f"Receiving file: {filename} ({file_size} bytes)")
                    
                    # Ask user for save location
                    save_dir = filedialog.askdirectory(title=f"Save '{filename}' to:")
                    if not save_dir:
                        self.log("File save canceled")
                        client_sock.close()
                        continue
                    
                    save_path = os.path.join(save_dir, filename)
                    
                    # Receive the file
                    with open(save_path, 'wb') as f:
                        bytes_received = 0
                        while bytes_received < file_size and self.receiving:
                            try:
                                data = client_sock.recv(1024)
                                if not data:
                                    break
                                f.write(data)
                                bytes_received += len(data)
                            except socket.timeout:
                                continue
                    
                    self.log(f"File saved to: {save_path}")
                except Exception as e:
                    self.log(f"Error receiving file: {e}")
                finally:
                    client_sock.close()
                    
            except socket.timeout:
                # This is just to check the receiving flag periodically
                continue
            except Exception as e:
                self.log(f"Socket error: {e}")
                time.sleep(1)  # Prevent CPU spike on repeated errors
        
        # Clean up
        try:
            server_sock.close()
        except:
            pass
    
    def _get_local_ip(self):
        """Get local IP address"""
        try:
            # Create a socket that connects to an external address
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

def main():
    root = tk.Tk()
    app = FileTransferApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()