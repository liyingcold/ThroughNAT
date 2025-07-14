import socket
import json

server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server.bind(('0.0.0.0' , 9999))#监听所有网卡
print("信令服务器启动，端口：9999")

devices = {}

while True:
    # 接收客户端消息（recvfrom常用于UDP套接字，最多1024字节）
    data , addr = server.recvfrom(1024)

    try:
        msg = json.loads(data.decode())#反序列化，字符串转为python对象
        device_id = msg['id']

        if msg['type'] == 'register':
            #记录设备公网地址（NAT映射后的地址）
            devices[device_id] = {
                'public_addr': addr,#IP,端口
                'local_addr': msg['local_addr'] #内网地址
            }
            print(f"设备注册：{device_id} :公网{addr} 内网{msg['local_addr']}")

            #当有两个设备时交换地址
            if len(devices) == 2:
                ids = list(devices.keys())
                for i in range(2):
                    peer_id = ids[1] if i == 0 else ids[0]
                    peer_info = {
                        'id': peer_id,
                        'public_addr': devices[peer_id]['public_addr'],
                        'local_addr': devices[peer_id]['local_addr']
                    }
                    server.sendto(json.dumps(peer_info).encode(),devices[ids[i]]['public_addr'])
                    print(f"已发送 {ids[i]} -> {peer_id} 的地址")
    except Exception as e:
        print(f"错误： {str(e)}")

