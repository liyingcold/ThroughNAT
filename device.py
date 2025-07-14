import json
import socket
import threading
import time

def get_local_ip():
    """获取本地IP地址（内网地址）"""
    s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)#获取一个UDP/IP套接字
    try:
        s.connect(("8.8.8.8", 80))#初始化连接
        return s.getsockname()[0]#返回地址
    finally:
        s.close()

class Device:
    def __init__(self,device_id):
        self.id = device_id
        self.sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.sock.bind(('0.0.0.0', 0)) #绑定随机端口
        self.peer_addr = None
        self.peer_connected = False #标记直连是否成功
        self.relay_active = False #标记是否启用中继模式
        self.relay_server_addr = ('your.relay.server.ip',10000) #中继服务器地址

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

        #启动接收线程（target指定运行函数，daemon设置守护线程，未守护线程结束则结束，不管该线程是否执行完成）
        threading.Thread(target = self.listen, daemon=True).start()

    def start_communication(self, peer_info):
        """
        尝试建立连接的主方法
        先尝试直连穿透，失败后启用中继模式
        """
        print("\n===== 开始连接流程 =====")

        #1、尝试直接穿透
        self.punch_hole(peer_info)
        #2、等待5秒检测是否穿透成功
        print("等待5s穿透结果")
        time.sleep(5)

        #3、检查是否建立直连
        if self.peer_connected:
            print("======= 直连穿透成功 =======")
            self.start_chat_session()
        else:
            print("======= 直连穿透失败，启用中继模式 =======")
            self.enable_relay_mode(peer_info)

    def enable_relay_mode(self, peer_info):
        """启用中继后备方案"""
        try:
            self.relay_active = True

            #1、向中继服务器注册，json字符串
            register_msg = json.dumps({
                'action': 'register',
                'device_id': self.id,
                'peer_id': peer_info['id']
            })
            self.sock.sendto(register_msg.encode(),self.relay_server_addr)
            print(f"已向中继服务器注册： {self.id}")

            #2、启动中继消息监听线程
            threading.Thread(target=self.listen_relay_messages, daemon=True).start()

            #3、启动中继消息发送线程
            threading.Thread(target=self.send_relay_messages, daemon=True).start()

            print("中继模式已启动，输入消息开始通信...")
        except Exception as e:
            print(f"启用中继模式失败： {str(e)}")

    def listen_relay_messages(self):
        """监听中继服务器转发的消息"""
        while self.relay_active:
            try:
                data, addr = self.sock.recvfrom(1024)

                #只处理来自中继服务器的消息
                if addr == self.relay_server_addr:
                    message = json.loads(data.decode())

                    if message['type'] == 'relay':
                        print(f"\n[来自 {message['from']}的中继消息] {message['content']}")
                    elif message['type'] == 'system':
                        print(f"\n[系统消息 {message['content']}]")

            except socket.timeout:
                pass #正常超时，继续循环
            except Exception as e:
                print(f"中继接受错误：{str(e)}")
                break

    def send_relay_messages(self):
        """通过中继服务器发送消息"""
        while self.relay_active:
            try:
                #获取用户输入信息
                message = input("输入内容（输入‘exit’退出）")
                if message.lower() == 'exit' :
                    self.relay_active = False
                    break

                #构建中继消息
                relay_msg = json.dumps({
                    'action': 'send',
                    'from': self.id,
                    'content': message
                })

                #发送到中继服务器
                self.sock.sendto(relay_msg.encode(), self.relay_server_addr)
                print(f"[已发送] {message}")

            except Exception as e:
                print(f"发送中继消息错误： {str(e)}")

    def start_chat_session(self):
        """直连成功后的会话"""
        print("直连已建立，输入消息开始会话...")
        threading.Thread(target=self.listen_direct_messages, daemon=True).start()
        while True:
            try:
                message = input("输入消息（输入‘exut’退出）：")
                if message.lower() == 'exit':
                    break
                
                #发送到对端设备
                self.sock.sendto(message.encode(),self.peer_addr)
                print(f"[已发送] {message}")
                
            except Exception as e:
                print(f"发送消息所悟： {str(e)}")
    
    def listen_direct_messages(self):
        """监听直连消息"""
        while True:
            try:
                data, addr  = self.sock.recvfrom(1024)
                if addr == self.peer_addr:
                    print(f"\n[来自对端] {data.decode()}")
            except:
                break


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

# if __name__ == "__main__":
#     device_id = input("输入设备ID(e.g.,DEVICE_A)：")
#     server_ip = input("信令服务器IP:")
#
#     dev = Device(device_id)
#     dev.register(server_ip)
#
#     #等待服务器返回对端消息
#     data, _ = dev.sock.recvfrom(1024)
#     peer_info = json.loads(data.decode())
#     print(f"\n收到对端信息： {peer_info['id']}")
#
#     time.sleep(1) #等待对方准备
#     dev.punch_hole(peer_info)
#
#     #保持主线程运行
#     input("按Enter退出...")

if __name__ == "__main__":
    device_id = input("输入设备ID(e.g.,DEVICE_A)：")
    server_ip = input("信令服务器IP:")

    dev = Device(device_id)
    dev.register(server_ip)

    #等待服务器返回对端消息
    print("等待对端信息...")
    data, _ = dev.sock.recvfrom(1024)
    peer_info = json.loads(data.decode())
    print(f"\n收到对端信息： {peer_info['id']}")

    #设置超时，避免recvfrom永久阻塞
    dev.sock.settimeout(5.0)
    #启动连接流程
    dev.start_communication(peer_info)

    #主线程等待
    input("按Enter退出...")