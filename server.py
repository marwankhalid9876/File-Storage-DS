import socket
import threading
import time

import sys
import utils.utils_server as utils
import json

class Server:

    SERVER_UDP_PORT = 5000
    TIMEOUT = 2
    HEARTBEAT_INTERVAL = 1

    def __init__(self):
        self.server_ip = f"{socket.gethostbyname(socket.gethostname())}"
        self.server_tcp_port = self.get_available_port()
        self.is_leader = False
        self.servers = []
        self.leader = None
        self.last_heartbeat = {}  # Dictionary to store the last heartbeat time of each server

        self.HEARTBEAT_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.HEARTBEAT_SOCKET.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.HEARTBEAT_SOCKET.bind((self.server_ip, 0)) # bind to a random available port

    def broadcast_message(self, message):
        for server in self.servers:
            print(f"Sending message to {server}")
            try:
                with socket.create_connection((server['ip'], server['port']), timeout=2) as multicast_socket:
                    multicast_socket.send(message.encode())
            except socket.error as e:
                    print("Could not connect to server: ", server)
                    # self.servers.remove(server)
                    # print(f"Removed dead server: {server}")

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
            print(f"Received message: {message.strip()}")
            if message == 'HEARTBEAT':
                continue

            elif message.startswith('GET_TREE'):
                print("Received GET_TREE")
                threading.Thread(target=self.handel_get_tree, args=(addr, message)).start()
                continue

            elif message.startswith('read'):
                print("Received READ")
                threading.Thread(target=self.handel_read_file, args=(addr, message)).start()
                continue

            elif message.startswith('write'):
                print("Received WRITE")
                #self.handel_write(addr, message, client_socket)
                threading.Thread(target=self.handel_write_file, args=(addr, message, client_socket)).start()
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
                # handel requests
                # get_stuff(message, addr)
                # threading.Thread(target=utils.server_main_app, args=(client_socket,)).start()

            else:
                print("Message received from Leader")

    def listen_for_UDP(self):
        print("Listening for UDP Messages...")
        listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listen_socket.bind(('0.0.0.0', Server.SERVER_UDP_PORT))

        while True:
            message, addr = listen_socket.recvfrom(1024)
            #print(f"Received response from {addr}")
            decoded_message = message.decode()
            if decoded_message.startswith('DISCOVER'):
                threading.Thread(target=self.handel_discover, args=(addr, decoded_message)).start()
            elif decoded_message.startswith('WHO_IS_THE_LEADER'):
                threading.Thread(target=self.handel_who_is_leader, args=(addr, decoded_message)).start()
            elif decoded_message.startswith('OK'):
                threading.Thread(target=self.handel_ok, args=(addr, decoded_message)).start()
            elif decoded_message.startswith('HEARTBEAT'):
                threading.Thread(target=self.handel_heartbeat, args=(addr, decoded_message)).start()
            # elif decoded_message.startswith('GET_TREE'):
            #     threading.Thread(target=self.handel_get_tree, args=(addr, decoded_message)).start()
            # else:
            #     print(f"Received from Leader: {decoded_message}")

    def handel_discover(self, addr, message):

        _, port = message.split(':')

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
            send_ack_socket.sendto(f'OK:{self.server_tcp_port}'.encode(), (addr[0], Server.SERVER_UDP_PORT))
    
    def handel_who_is_leader(self, addr, message):
        _, port = message.split(':')
        print("Received WHO_IS_LEADER")
        # send back I_AM_THE_LEADER:{port} if self.is_leader, otherwise do not respond
        if self.is_leader:
            send_ack_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            send_ack_socket.bind((self.server_ip, 0))
            send_ack_socket.connect((addr[0], int(port)))
            send_ack_socket.send(f'I_AM_THE_LEADER:{self.server_tcp_port}'.encode())
            send_ack_socket.close()

    def handel_ok(self, addr, message):
        _, port = message.split(':')
        server_config = {'ip': addr[0], 'port': int(port)}
        if server_config != {'ip': self.server_ip, 'port': self.server_tcp_port}:
            if server_config not in self.servers:
                print(f"Adding server: {server_config} to discovered servers")
                self.servers.append(server_config)

                self.elect_leader()

    def handel_heartbeat(self, addr, message):
        _, port = message.split(':')
        # print("Received HEARTBEAT")
        self.last_heartbeat[f"{addr[0]}:{port}"] = time.time()

    def handel_get_tree(self, addr, message):
        r"""Sends the directory tree to the client"""

        _, port = message.split(':')
        if self.is_leader:
            tree = utils.build_directory_tree('DB/')
            tree = json.dumps(tree)
            tree = f"TREE:{tree}"

            send_ack_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            send_ack_socket.connect((addr[0], int(port)))
            send_ack_socket.send(tree.encode())
            send_ack_socket.close()

    def handel_read_file(self, addr, message):
        r"""Sends the File to the client"""

        operation, port, file_path = message.split(':')
        port = int(port)

        send_file_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        send_file_socket.connect((addr[0], int(port)))
        send_file_socket.send(f"FILE:{file_path.split('/')[-1]}".encode())
        utils.send_file(file_path, send_file_socket)
        send_file_socket.close()

    def handel_write_file(self, addr, message, client_socket):
        r""""""

        operation, port, file_path = message.split(':')
        file_path = file_path.strip()
        port = int(port)

        utils.receive_file(file_path, client_socket)

        # inform other servers to update their files
        
        # send <DONE> to client
        send_done_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        send_done_socket.connect((addr[0], int(port)))
        send_done_socket.send("<DONE>".encode())
        send_done_socket.close()

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
    
    def send_heartbeat(self):
        while True:
            self.HEARTBEAT_SOCKET.sendto(f"HEARTBEAT:{self.server_tcp_port}".encode(), ('<broadcast>', Server.SERVER_UDP_PORT))
            time.sleep(Server.HEARTBEAT_INTERVAL)

    def check_last_heartbeat(self):
        while True:
            for addr, last_time in list(self.last_heartbeat.items()):
                if time.time() - last_time > Server.TIMEOUT:
                    print(f"Server {addr} has died")
                    ip, port = addr.split(':')
                    dead_server = {'ip': ip, 'port': int(port)}
                    self.servers.remove(dead_server)
                    del self.last_heartbeat[addr]
            time.sleep(Server.HEARTBEAT_INTERVAL)  # Check Servers every second

    def get_available_port(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            port = s.getsockname()[1]
        return port

    def print_servers(self):
        print("*"*20)
        
        print("All Running Servers: ")
        print("-", {'ip': self.server_ip, 'port': self.server_tcp_port}, "(Me)")
        for server in self.servers:
            print("-", server)
        print("*"*20)

    def start(self):
        threading.Thread(target=self.listen_for_UDP, daemon=True).start()
        threading.Thread(target=self.listen_for_TCP, daemon=True).start()

        self.discover_hosts()
        time.sleep(2)

        self.print_servers()

        self.elect_leader()
        time.sleep(2)
        #threading.Thread(target=self.heartbeat).start()
        threading.Thread(target=self.send_heartbeat, daemon=True).start()
        threading.Thread(target=self.check_last_heartbeat, daemon=True).start()
        print("Server Started...")

if __name__ == '__main__':
    server = Server()
    server.start()
    while True:
        pass