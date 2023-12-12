import socket
import threading
import time
import sys
from server import server_main_app
port = 8888
class Server:
    port_list = [8887, 8888, 8889]

    def __init__(self, server_port):
        self.server_ip = "0.0.0.0" #f"{socket.gethostbyname(socket.gethostname())}"
        print(self.server_ip)
        self.server_port = server_port
        self.is_leader = False
        self.servers = []
        self.leader = None

    def broadcast_message(self, message):
        for server in self.servers:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.connect((server['ip'], server['port']))
            server_socket.send(message.encode())
            server_socket.close()

    def discover_hosts(self):
        print("Discovering hosts...")
        discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        for port in Server.port_list:
            if port == self.server_port:
                continue
            else:
                discovery_socket.sendto(f'DISCOVER:{self.server_port}'.encode(), ('<broadcast>', port))

    def listen_for_client(self):
        listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listen_socket.bind((self.server_ip, self.server_port))
        listen_socket.listen(5)

        while True:
            client_socket, addr = listen_socket.accept()
            message = client_socket.recv(1024).decode()
            if message == 'HEARTBEAT':
                continue

            if self.is_leader:
                # if leader, broadcast message to all servers
                print("Forwarding message from client to all servers")
                #DO THE FORWARDING HERE
                
                self.broadcast_message(message)
                # do what ever you have to do
                print("Message Content: ", message)
                print("Message Processed")
                # server_main_app(client_socket)
                threading.Thread(target=server_main_app, args=(client_socket,)).start()

            else:
                print("Message received from Leader")

            

    def listen_for_broadcast(self):
        print("Listening for broadcast...")
        listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        listen_socket.bind((self.server_ip, self.server_port))

        while True:
            message, addr = listen_socket.recvfrom(1024)
            #print(f"Received response from {addr}")
            decoded_message = message.decode()
            threading.Thread(target=self.handel_discover_broadcast, args=(addr, decoded_message)).start()

    def handel_discover_broadcast(self, addr, message):
        message_body, port = message.split(':')
        if message_body=='DISCOVER':
            # discover message
            server_config = {'ip': addr[0], 'port': int(port)}
            if server_config not in self.servers:
                print(f"Adding server: {server_config} to discovered servers")
                self.servers.append(server_config)
                #Q: WHY DO WE NEED TO DISCOVER HOSTS AGAIN?
                #Q: WHY DO WE NEED TO ELECT LEADER AGAIN?
                self.discover_hosts()
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
                send_ack_socket.sendto(f'I_AM_THE_LEADER:{self.server_port}'.encode(), (addr[0], int(port)))
    
    def elect_leader(self):
        self.previous_leadership = self.is_leader
        self.is_leader = True
        for server in self.servers:
            if f"{server['port']}" > f"{self.server_port}":
                self.is_leader = False

        if self.is_leader and (self.is_leader!=self.previous_leadership):
            self.leader_ip = self.server_ip
            self.leader_port = self.server_port
            self.broadcast_message('NEW_LEADER')

        print(f"Am I Leader: {self.is_leader}")

    def heartbeat(self):
        r"""Sends a heartbeat to all servers"""

        while True:
            dead_servers = []
            for server in self.servers:
                try:
                    with socket.create_connection((server['ip'], server['port']), timeout=1) as heartbeat_socket:
                        heartbeat_socket.send("HEARTBEAT".encode())
                except socket.error:
                    dead_servers.append(server)

            for server in dead_servers:
                self.servers.remove(server)
                print(f"Removed dead server: {server}")

                self.discover_hosts()
                self.elect_leader()

            time.sleep(1)

    def print_servers(self):
        print("*"*20)
        
        print("All Running Servers: ")
        print("-", {'ip': self.server_ip, 'port': self.server_port}, "(Me)")
        for server in self.servers:
            print("-", server)
        print("*"*20)

    def start(self):
        threading.Thread(target=self.listen_for_broadcast).start()
        threading.Thread(target=self.listen_for_client).start()

        self.discover_hosts()
        time.sleep(2)

        self.print_servers()

        self.elect_leader()
        time.sleep(2)
        threading.Thread(target=self.heartbeat).start()
        print("Server Started...")

if __name__ == '__main__':
    # port = int(sys.argv[1])
    #is_leader = True if sys.argv[2].lower() == 'true' else False
    server = Server(server_port=port)#, is_leader=is_leader)
    server.start()