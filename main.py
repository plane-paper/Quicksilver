from wlan.ipReceiver import execute, get_devices_formatted, get_devices_by_model, format_system_info
if __name__ == "__main__":
    
    print("扫描设备中(等待5秒)...")
    devices = get_devices_by_model(timeout=5)
    print(f"发现 {len(devices)} 个设备:")
    
    formatted = format_system_info(devices)
    print("\n按型号分类的设备列表:")
    print(formatted)