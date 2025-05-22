import tkinter as tk
from tkinter import ttk, filedialog, messagebox, PhotoImage
import threading
import os
import time
import sys

# Import WLAN modules - using absolute imports
import wlan.ipReceiver as ipReceiver
import wlan.wlan_sender as wlan_sender
import wlan.ipBroadcast as ipBroadcast
import wlan.wlan_receiver as wlan_receiver

# Import Bluetooth modules
import blue.bluetooth_sender as bluetooth_sender
import blue.bluetooth_receiver as bluetooth_receiver

def resource_path(relative_path):
    """Get the absolute path to a resource, works for dev and PyInstaller"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class FileTransferApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Quicksilver: File Transfer")
        self.root.geometry("600x500")
        self.root.configure(padx=20, pady=20)
        root.iconphoto(True, PhotoImage(file=resource_path('assets/logo_cropped.png')))

        
        self.sending = False
        self.receiving = False
        self.receiver_stop_flag = threading.Event()
        self.broadcast_stop_flag = threading.Event()
        
        self.file_path = tk.StringVar()
        self.send_method = tk.StringVar(value="Wi-Fi")
        self.selected_device = None
        self.devices_list = []
        
        self.create_notebook()
        
        # Start broadcasting in background
        # self.start_background_broadcast()
        
        # Auto-start receiver with default method (Wi-Fi)
        self.root.after(1000, self.auto_start_receiver)  # Start after 1 second to ensure UI is ready
        
    def auto_start_receiver(self):
        """Automatically start the receiver when the app launches"""
        if not self.receiving:
            self.start_receiver()
        
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
        
        self.progress_bar = ttk.Progressbar(status_frame, orient="horizontal", mode="determinate")
        
        # Send button
        self.send_button = ttk.Button(parent, text="Send", command=self.send_file)
        self.send_button.pack(pady=(10, 0))
        
        # Initially populate devices list
        self.refresh_devices()
    
    def build_receive_ui(self, parent):
        """Build the UI for receiving files"""
        # Information frame
        info_frame = ttk.LabelFrame(parent, text="Receiver Settings")
        info_frame.pack(fill="x", pady=(0, 10))
        
        self.receive_method = tk.StringVar(value="Wi-Fi")
        wifi_radio = ttk.Radiobutton(info_frame, text="Wi-Fi", variable=self.receive_method, 
                       value="Wi-Fi", command=self.on_receive_method_change)
        wifi_radio.pack(anchor="w")
        
        bt_radio = ttk.Radiobutton(info_frame, text="Bluetooth", variable=self.receive_method,
                       value="Bluetooth", command=self.on_receive_method_change)
        bt_radio.pack(anchor="w")
        
        # Status indicators
        self.receiver_status = ttk.Label(info_frame, text="Receiver is OFF", foreground="red")
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
        
        # Add scrollbar to log
        log_scroll_frame = ttk.Frame(log_frame)
        log_scroll_frame.pack(fill="both", expand=True)
        
        self.log_text = tk.Text(log_scroll_frame, height=10, wrap="word")
        log_scrollbar = ttk.Scrollbar(log_scroll_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side="left", fill="both", expand=True)
        log_scrollbar.pack(side="right", fill="y")
    
    def on_receive_method_change(self):
        """Handle change in receive method selection"""
        if self.receiving:
            # If receiver is currently running, restart it with the new method
            method = self.receive_method.get()
            self.log(f"Switching receiver method to {method}")
            self.stop_receiver(target_method=method)
            # Give a short delay before restarting
            self.root.after(500, self.start_receiver)
        
    def log(self, message):
        """Add a message to the log with timestamp"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.see("end")
        self.root.update_idletasks()
    
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
        self.progress_bar.pack(side="right", fill="x", expand=True, padx=(10, 0))
        self.progress_bar.config(mode="indeterminate")
        self.progress_bar.start()
        
        # Run device discovery in a thread
        threading.Thread(target=self._refresh_devices_thread, daemon=True).start()
    
    def _refresh_devices_thread(self):
        """Background thread to discover devices"""
        method = self.send_method.get()
        
        try:
            if method == "Wi-Fi":
                # Use existing ipReceiver module
                models = ipReceiver.get_devices_by_model(timeout=3)
                self.devices_list = []
                
                for model in sorted(models.keys()):
                    for device in models[model]:
                        display_text = f"{device['name']} [{device['ip']}] - {ipReceiver.format_time_ago(device['last_seen'])}"
                        self.devices_list.append({
                            'display': display_text,
                            'ip': device['ip'],
                            'name': device['name'],
                            'mac': device['mac'],
                            'type': 'wifi'
                        })
            else:
                # Use existing bluetooth_sender module
                bt_devices = bluetooth_sender.discover_devices()
                self.devices_list = []
                
                for addr, name in bt_devices:
                    display_text = f"{name} [{addr}]"
                    self.devices_list.append({
                        'display': display_text,
                        'addr': addr,
                        'name': name,
                        'type': 'bluetooth'
                    })
        except Exception as e:
            self.root.after(0, lambda: self.log(f"Error discovering devices: {e}"))
        
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
    
    def update_progress(self, bytes_sent, total_size):
        """Update progress bar during file transfer"""
        if total_size > 0:
            progress = (bytes_sent / total_size) * 100
            self.progress_bar.config(value=progress)
            self.status_label.config(text=f"Sending... {progress:.1f}%")
            self.root.update_idletasks()
    
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
        self.status_label.config(text="Connecting...")
        self.progress_bar.config(mode="determinate", value=0)
        self.progress_bar.pack(side="right", fill="x", expand=True, padx=(10, 0))
        
        # Run the transfer in a background thread
        threading.Thread(target=self._send_file_thread, daemon=True).start()
    
    def _send_file_thread(self):
        """Background thread to handle file sending"""
        success = False
        try:
            method = self.send_method.get()
            file_path = self.file_path.get()
            
            if method == "Wi-Fi" and self.selected_device['type'] == 'wifi':
                # Use existing wlan_sender module
                ip = self.selected_device['ip']
                self.root.after(0, lambda: self.status_label.config(text=f"Connecting to {ip}..."))
                success = wlan_sender.send_file_to_device(
                    ip, file_path, 
                    progress_callback=lambda sent, total: self.root.after(0, lambda: self.update_progress(sent, total)),
                    log_callback=lambda msg: self.root.after(0, lambda: self.log(msg))
                )
            elif method == "Bluetooth" and self.selected_device['type'] == 'bluetooth':
                # Use existing bluetooth_sender module
                addr = self.selected_device['addr']
                self.root.after(0, lambda: self.status_label.config(text=f"Connecting to {addr}..."))
                success = bluetooth_sender.send_file_to_device(
                    addr, file_path,
                    progress_callback=lambda sent, total: self.root.after(0, lambda: self.update_progress(sent, total)),
                    log_callback=lambda msg: self.root.after(0, lambda: self.log(msg))
                )
            else:
                self.root.after(0, lambda: messagebox.showerror("Error", "Device type mismatch"))
                return
                
            # Show result
            if success:
                self.root.after(0, lambda: messagebox.showinfo("Success", "File sent successfully"))
            else:
                self.root.after(0, lambda: messagebox.showerror("Error", "Failed to send file"))
                
        except Exception as e:
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
        print("DEBUG: start_background_broadcast function called")
        self.broadcast_stop_flag.clear() # So the broadcast can always start when this function is called
        """Start broadcasting system info in background"""
        def broadcast_loop():
            try:
                ipBroadcast.start_broadcasting_loop(self.broadcast_stop_flag)
            except Exception as e:
                print(f"Broadcast error: {e}")
        
        self.broadcast_thread = threading.Thread(target=broadcast_loop, daemon=True)
        self.broadcast_thread.start()

    def stop_background_broadcast(self):
        print("DEBUG: stop_background_broadcast function called")
        self.broadcast_stop_flag.set()
        if hasattr(self, 'broadcast_thread') and self.broadcast_thread.is_alive():
            self.broadcast_thread.join(timeout=1)
    
    def start_receiver(self):
        """Start the receiver based on selected method"""
        if self.receiving:
            return
        
        method = self.receive_method.get()
        self.log(f"Starting {method} receiver...")
        
        self.receiving = True
        self.receiver_stop_flag.clear()
        self.start_receiver_btn.config(state="disabled")
        self.stop_receiver_btn.config(state="normal")
        
        # Start receiver in background thread
        self.receiver_thread = threading.Thread(target=self._run_receiver, daemon=True)
        self.receiver_thread.start()
        
        # Update UI
        if method == "Wi-Fi":
            ip = self._get_local_ip()
            self.receiver_status.config(text="Wi-Fi Receiver is ACTIVE", foreground="green")
            self.receiver_info.config(text=f"Listening on {ip}:54321")
            self.start_background_broadcast()
        else:
            self.receiver_status.config(text="Bluetooth Receiver is ACTIVE", foreground="green")
            self.receiver_info.config(text="Bluetooth device is discoverable")
            
    
    def stop_receiver(self, target_method):
        """Stop the active receiver"""
        if not self.receiving:
            return
        
        self.log("Stopping receiver...")
        self.receiving = False
        self.receiver_stop_flag.set()
        if target_method == "Bluetooth":
            self.stop_background_broadcast()
            self.broadcast_stop_flag.clear()

        # Update UI
        self.start_receiver_btn.config(state="normal")
        self.stop_receiver_btn.config(state="disabled")
        self.receiver_status.config(text="Receiver is OFF", foreground="red")
        self.receiver_info.config(text="")

    def gui_save_callback(self, filename):
        """GUI callback for file save dialog"""
        save_path = filedialog.asksaveasfilename(
            title=f"Save '{filename}' as:",
            initialfile=filename,
            defaultextension="*",
            filetypes=[("All files", "*.*")]
        )
        return save_path if save_path else None

    def _run_receiver(self):
        """Run the appropriate receiver in a background thread"""
        
        
        while self.receiving and not self.receiver_stop_flag.is_set():
            method = self.receive_method.get()
            try:
                if method == "Wi-Fi":
                    # Use existing wlan_receiver module
                    success = wlan_receiver.receive_file_blocking(
                        host='0.0.0.0', 
                        port=54321,
                        gui_callback=self.gui_save_callback,
                        log_callback=lambda msg: self.root.after(0, lambda: self.log(msg)),
                        stop_flag=self.receiver_stop_flag
                    )
                    if success:
                        self.root.after(0, lambda: self.log("File received successfully - receiver still active"))
                    # Continue the loop to keep receiving more files
                else:
                    
                    # Use existing bluetooth_receiver module
                    success = bluetooth_receiver.start_receiver_blocking(
                        gui_callback=self.gui_save_callback,
                        progress_callback=None,
                        log_callback=lambda msg: self.root.after(0, lambda: self.log(msg))
                    )
                    if success:
                        self.root.after(0, lambda: self.log("File received successfully - receiver still active"))
                    # Continue the loop to keep receiving more files
                        
            except Exception as e:
                if self.receiving:  # Only log error if we're still supposed to be receiving
                    self.root.after(0, lambda: self.log(f"Error in receiver: {e}"))
                    # Brief pause before retrying
                    time.sleep(1)
        
        # Clean up when loop exits
        self.root.after(0, lambda: self.log("Receiver stopped"))
    
    def _get_local_ip(self):
        """Get local IP address"""
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    def on_closing(self):
        """Handle application closing"""
        self.broadcast_stop_flag.set()
        self.receiver_stop_flag.set()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = FileTransferApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()