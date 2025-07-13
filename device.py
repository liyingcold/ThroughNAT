import json
import socket
import threading
import time

def get_local_ip():
    """获取本地IP地址（内网地址）"""
    s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()

class Device:
    def __init__(self,device_id):
        self.id = device_id
        self.sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.sock.bind(('0.0.0.0', 0)) #绑定随机端口
        self.peer_addr = None
        # self.peer_connected = False #标记直连是否成功
        # self.relay_active = False #标记是否启用中继模式
        # self.relay_server_addr = ('your.relay.server.ip',10000) #中继服务器地址

    def register(self, server_ip):
        """向信令服务器注册"""
        local_ip = get_local_ip()
        local_port = self.sock.getsockname()[1]
        message = json.dumps({
            'type': 'register',
            'id': self.id,
            'local_addr': f"{local_ip}:{local_port}"
        })
        self.sock.sendto(message.encode(),(server_ip,9999))

    def punch_hole(self,peer_info):
        """尝试穿透连接"""
        public_addr = tuple(peer_info['public_addr'])
        local_addr = tuple(peer_info['local_addr'].split(':'))

        print(f"尝试连接 {peer_info['id']}:")
        print(f" - 公网地址： {public_addr[0]}:{public_addr[1]}")
        print(f" - 内网地址： {local_addr[0]:{local_addr[1]}}")

        #同时尝试公网和内网地址（提高成功率）
        for target in [public_addr,local_addr]:
            try:
                self.sock.sendto(f"PUNCH from {self.id}".encode(),target)
                print(f"已向 {target}发送穿透包")
            except Exception as e:
                print(f"发送错误： {str(e)}")

        #启动接收线程
        threading.Thread(target = self.listen, daemon=True).start()

    def listen(self):
        """监听传入消息"""
        while True:
            try:
                data, addr = self.sock.recvfrom(1024)
                print(f"\n穿透成功！收到来自 {addr} 的消息：{data.decode()}")
                #确认连接后开始通信
                self.sock.sendto(f"HELLO {addr}!".encode(), addr)
            except Exception as e:
                print(f"接收错误： {str(e)}")
                break

if __name__ == "__main__":
    device_id = input("输入设备ID(e.g.,DEVICE_A)：")
    server_ip = input("信令服务器IP:")

    dev = Device(device_id)
    dev.register(server_ip)

    #等待服务器返回对端消息
    data, _ = dev.sock.recvfrom(1024)
    peer_info = json.loads(data.decode())
    print(f"\n收到对端信息： {peer_info['id']}")

    time.sleep(1) #等待对方准备
    dev.punch_hole(peer_info)

    #保持主线程运行
    input("按Enter退出...")