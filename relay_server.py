import socket
import json
import threading

class RelayServer:
    def __init__(self,host='0.0.0.0',port=10000):
        self.sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.sock.bind((host, port))
        self.devices = {} #存储设备信息: {device_id: address}
        self.pairs = {} #存储设备配对: {device1: device2, device2: device1}
        print(f"中继服务器启动在 {host}:{port}")

    def start(self):
        """启动服务器主循环"""
        while True:
            try:
                data, addr = self.sock.recvfrom(1024)
                #开启线程（args 指定需要的参数）
                threading.Thread(target=self.handle_message, args=(data, addr)).start()
            except Exception as e:
                print(f"服务器错误: {str(e)}")

    def handle_message(self, data, addr):
        """处理接收到的消息"""
        try:
            message = json.loads(data.decode())
            action = message.get('action')
            device_id = message.get('device_id')

            if action == 'register':
                self.handle_register(device_id, addr, message)

            elif action == 'send':
                self.handle_send(device_id, addr, message)

            else:
                self.send_system_message(addr, "未知操作")

        except json.JSONDecodeError:
            self.send_system_message(addr, "无效的JSON格式")
        except Exception as e:
            print(f"处理消息错误: {str(e)}")

    def handle_register(self, device_id, addr, message):
        """处理设备注册"""
        peer_id = message.get('peer_id')

        # 保存设备地址
        self.devices[device_id] = addr

        # 检查是否双方都注册了
        if peer_id in self.devices:
            # 配对设备
            self.pairs[device_id] = peer_id
            self.pairs[peer_id] = device_id

            # 通知双方配对成功
            self.send_system_message(addr, f"配对成功! 与 {peer_id} 建立中继连接")
            self.send_system_message(self.devices[peer_id], f"配对成功! 与 {device_id} 建立中继连接")

            print(f"设备配对: {device_id} <-> {peer_id}")
        else:
            self.send_system_message(addr, f"等待对端 {peer_id} 连接中继...")

    def handle_send(self, device_id, addr, message):
        """处理转发消息"""
        if device_id not in self.pairs:
            self.send_system_message(addr, "错误: 尚未配对")
            return

        peer_id = self.pairs[device_id]

        if peer_id not in self.devices:
            self.send_system_message(addr, "错误: 对端设备不在线")
            return

        # 构建转发消息
        relay_msg = json.dumps({
            'type': 'relay',
            'from': device_id,
            'content': message.get('content', '')
        })

        # 转发给对端
        peer_addr = self.devices[peer_id]
        self.sock.sendto(relay_msg.encode(), peer_addr)
        print(f"中继转发: {device_id} -> {peer_id}")

    def send_system_message(self, addr, content):
        """发送系统消息"""
        msg = json.dumps({
            'type': 'system',
            'content': content
        })
        self.sock.sendto(msg.encode(), addr)


if __name__ == "__main__":
    server = RelayServer()
    server.start()