import socket
import threading
import time
import sys

class Server:

    SERVER_UDP_PORT = 5000

    def __init__(self, server_tcp_port):
        self.server_ip = f"{socket.gethostbyname(socket.gethostname())}"
        self.server_tcp_port = server_tcp_port
        self.is_leader = False
        self.servers = []
        self.leader = None

    def broadcast_message(self, message):
        for server in self.servers:
            print(f"Sending message to {server}")
            with socket.create_connection((server['ip'], server['port']), timeout=2) as multicast_socket:
                multicast_socket.send(message.encode())

    def discover_hosts(self):
        print("Discovering hosts...")
        discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        discovery_socket.bind((self.server_ip, 0)) 

        discovery_socket.sendto(f'DISCOVER:{self.server_tcp_port}'.encode(), ('<broadcast>', Server.SERVER_UDP_PORT))

    def listen_for_TCP(self):
        listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listen_socket.bind((self.server_ip, self.server_tcp_port))
        listen_socket.listen(5)

        while True:
            client_socket, addr = listen_socket.accept()
            message = client_socket.recv(1024).decode()
            if message == 'HEARTBEAT':
                continue

            if self.is_leader:
                # if leader, broadcast message to all servers
                print("Forwarding message from client to all servers")
                self.broadcast_message(message)
            else:
                print("Message received from Leader")

            # do what ever you have to do
            print("Message Content: ", message)
            print("Message Processed")

    def listen_for_UDP(self):
        print("Listening for UDP Messages...")
        listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listen_socket.bind(('0.0.0.0', Server.SERVER_UDP_PORT))

        while True:
            message, addr = listen_socket.recvfrom(1024)
            #print(f"Received response from {addr}")
            decoded_message = message.decode()
            if decoded_message.startswith(('WHO_IS_THE_LEADER:', 'DISCOVER', 'I_AM_HERE')):
                threading.Thread(target=self.handel_discover_broadcast, args=(addr, decoded_message)).start()
            else:
                print(f"Received from Leader: {decoded_message}")

    def handel_discover_broadcast(self, addr, message):

        message_body, port = message.split(':')

        if message_body=='DISCOVER':
            # discover message
            server_config = {'ip': addr[0], 'port': int(port)}

            if server_config != {'ip': self.server_ip, 'port': self.server_tcp_port}:

                if server_config not in self.servers:

                    print(f"Adding server: {server_config} to discovered servers")
                    self.servers.append(server_config)

                    self.elect_leader()
                
                send_ack_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                # get available port
                send_ack_socket.bind((self.server_ip, 0))
                # should send server ip not port
                send_ack_socket.sendto(f'I_AM_HERE:{self.server_tcp_port}'.encode(), (addr[0], Server.SERVER_UDP_PORT))
    
        elif message_body=='I_AM_HERE':
            server_config = {'ip': addr[0], 'port': int(port)}
            if server_config != {'ip': self.server_ip, 'port': self.server_tcp_port}:
                if server_config not in self.servers:
                    print(f"Adding server: {server_config} to discovered servers")
                    self.servers.append(server_config)

                    self.elect_leader()
        
        elif message_body=='WHO_IS_THE_LEADER':
            print("Received WHO_IS_LEADER")
            # send back I_AM_THE_LEADER:{port} if self.is_leader, otherwise do not respond
            if self.is_leader:
                # send_ack_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                # send_ack_socket.connect((addr[0], int(port)))
                # send_ack_socket.send(f'I_AM_THE_LEADER:{self.server_port}'.encode())
                # send_ack_socket.close()

                send_ack_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                # get available port
                send_ack_socket.bind((self.server_ip, 0))
                # should send server ip not port
                send_ack_socket.sendto(f'I_AM_THE_LEADER:{self.server_tcp_port}'.encode(), (addr[0], int(port)))
                send_ack_socket.close()
    
    def elect_leader(self):
        self.previous_leadership = self.is_leader
        self.is_leader = True
        for server in self.servers:
            if f"{server['ip']}:{server['port']}" > f"{self.server_ip}:{self.server_tcp_port}":
                self.is_leader = False

        if self.is_leader and (self.is_leader!=self.previous_leadership):
            self.leader_ip = self.server_ip
            self.leader_port = self.server_tcp_port
            self.broadcast_message('NEW_LEADER')

        print(f"Am I Leader: {self.is_leader}")

    def heartbeat(self):
        r"""Sends a heartbeat to all servers"""

        while True:
            dead_servers = []
            # send to servers with larger ip only
            #sorted_servers = sorted(self.servers, key=lambda x: x['ip'])
            for server in self.servers:
                try:
                    with socket.create_connection((server['ip'], server['port']), timeout=2) as heartbeat_socket:
                        heartbeat_socket.send("HEARTBEAT".encode())
                except socket.error as e:
                    print(e)
                    dead_servers.append(server)

            for server in dead_servers:
                self.servers.remove(server)
                print(f"Removed dead server: {server}")
                # if all servers larger than me are dead, I am the leader
                self.discover_hosts()
                self.elect_leader()
                self.print_servers()

            time.sleep(1)
            # self.print_servers()

    def print_servers(self):
        print("*"*20)
        
        print("All Running Servers: ")
        print("-", {'ip': self.server_ip, 'port': self.server_tcp_port}, "(Me)")
        for server in self.servers:
            print("-", server)
        print("*"*20)

    def start(self):
        threading.Thread(target=self.listen_for_UDP).start()
        threading.Thread(target=self.listen_for_TCP).start()

        self.discover_hosts()
        time.sleep(2)

        self.print_servers()

        self.elect_leader()
        time.sleep(2)
        threading.Thread(target=self.heartbeat).start()
        print("Server Started...")

if __name__ == '__main__':
    port = int(sys.argv[1])
    server = Server(server_tcp_port=port)
    server.start()