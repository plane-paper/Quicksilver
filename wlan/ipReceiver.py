import socket
import json
from collections import defaultdict
from typing import Dict, List, Optional
import time

def format_time_ago(ts):
    delta = time.time() - ts
    if delta < 60:
        return f"{int(delta)}s ago"
    elif delta < 3600:
        return f"{int(delta // 60)}m ago"
    else:
        return f"{int(delta // 3600)}h ago"

def parse_message(data: bytes) -> Optional[dict]:
    """解析 JSON 格式的广播消息
    
    Args:
        data: 接收到的字节数据
        
    Returns:
        解析后的字典(所有键转为小写)，如果解析失败则返回None
    """
    try:
        info = json.loads(data.decode())  # 解析 JSON
        return {k.lower(): v for k, v in info.items()}  # 统一键为小写
    except json.JSONDecodeError:
        return None

def format_system_info(models: Dict[str, List[dict]]) -> str:
    """格式化系统信息为字符串
    
    Args:
        models: 按型号分类的设备字典
        
    Returns:
        格式化后的设备信息字符串
    """
    output = []
    for model in sorted(models.keys()):
        output.append(f"{model}:")
        for idx, device in enumerate(models[model], 1):
            output.append(f"{idx}. {device['name']} {device['ip']} {device['mac']} {format_time_ago(device['last_seen'])}")
        output.append("")  # 空行分隔
    return "\n".join(output)

def execute(timeout: float = None) -> Dict[str, dict]:
    """监听设备广播并返回发现的设备
    
    Args:
        timeout: 监听超时时间(秒)，None表示无限监听
        
    Returns:
        以MAC为键的设备字典，包含name, model, ip, mac信息
    """
    devices = {}  # 设备列表（MAC 作为唯一标识）
    start_time = time.time()

    # 创建 UDP socket
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', 12345))  # 绑定广播端口
        sock.setblocking(False)  # 设置非阻塞模式

        while True:
            # 检查超时
            if timeout is not None and (time.time() - start_time) > timeout:
                break

            # 尝试接收数据
            try:
                data, addr = sock.recvfrom(1024)
                info = parse_message(data)

                # 如果解析成功，更新设备信息
                if info:
                    required_fields = ['name', 'model', 'ip', 'mac']
                    if all(field in info for field in required_fields):
                        mac = info['mac'].lower()
                        devices[mac] = {
                            'name': info['name'],
                            'model': info['model'],
                            'ip': info['ip'],
                            'mac': mac,
                            'last_seen': time.time() # 记录最后一次接收时间
                        }
            except BlockingIOError:
                time.sleep(0.25)  # 没有数据时短暂等待
                continue

    return devices

def get_devices_by_model(timeout: float = None) -> Dict[str, List[dict]]:
    """获取按型号分类的设备列表
    
    Args:
        timeout: 监听超时时间(秒)
        
    Returns:
        按型号分类的设备字典
    """
    devices = execute(timeout)
    models = defaultdict(list)
    for device in devices.values():
        models[device['model']].append(device)
    return dict(models)

def get_devices_formatted(timeout: float = None) -> str:
    """获取格式化后的设备信息字符串
    
    Args:
        timeout: 监听超时时间(秒)
        
    Returns:
        格式化后的设备信息字符串
    """
    models = get_devices_by_model(timeout)
    return format_system_info(models)