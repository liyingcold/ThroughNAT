# 基于python3.12的极简NAT穿透通信Demo

## 架构概述
```mermaid
graph TD
    A[内网设备A] -->|1.注册| S[信令服务器]
    B[内网设备B] -->|1.注册| S
    S -->|2.交换地址| A
    S -->|2.交换地址| B
    A -->|3.穿透尝试| B
    B -->|4.响应穿透| A
    A -->|穿透失败| R[中继服务器]
    R -->|转发数据| B
```
### 信令服务器工作原理
```mermaid
sequenceDiagram
    participant A as 设备A
    participant S as 信令服务器
    participant B as 设备B
    
    A->>S: 注册[公网IP_A:端口A]
    B->>S: 注册[公网IP_B:端口B]
    S->>A: 发送B的地址
    S->>B: 发送A的地址
    
    Note over A,B: 关键穿透步骤
    A->>B: 发送数据包（打开A的NAT）
    B->>A: 回复数据包（打开B的NAT）
    A->>B: 穿透成功！直接通信
```
#### 20250713单机模拟穿透（无中继转发逻辑）
##### 操作步骤
    1、打开三个终端窗口；
    2、窗口1：运行服务器 python server.py
    3、窗口2：运行设备A python device.py
       输入ID：DEVICE_A
       服务器IP：127.0.0.1
    4、窗口3：运行设备B python device.py
       输入ID：DEVICE_B
       服务器IP：127.0.0.1
##### 预期结果
###### 设备A输出
    收到对端信息: DEVICE_B
    尝试连接 DEVICE_B:
      - 公网地址: 127.0.0.1:53902
      - 内网地址: 192.168.1.100:53902
    已向 ('127.0.0.1', 53902) 发送穿透包
    已向 ('192.168.1.100', 53902) 发送穿透包
    穿透成功！收到来自 ('127.0.0.1', 53902) 的消息: PUNCH from DEVICE_B
    
### 中继模式工作原理
```mermaid
sequenceDiagram
    participant A as 设备A
    participant R as 中继服务器
    participant B as 设备B
    
    A->>R: 注册(device_id=DEVICE_A, peer_id=DEVICE_B)
    B->>R: 注册(device_id=DEVICE_B, peer_id=DEVICE_A)
    R->>A: 系统消息: 配对成功!
    R->>B: 系统消息: 配对成功!
    
    A->>R: 发送消息 "Hello"
    R->>B: 中继转发: [来自DEVICE_A] Hello
    
    B->>R: 发送回复 "Hi there!"
    R->>A: 中继转发: [来自DEVICE_B] Hi there!
```
