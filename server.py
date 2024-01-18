import socket
import threading
import time

import sys
import utils.utils_server as utils
import json
import os

class Server:

    SERVER_UDP_PORT = 5000
    TIMEOUT = 3
    HEARTBEAT_INTERVAL = 0.2
    T_Phase1 = 10
    T_Phase2 = 10

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

        self.broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.broadcast_socket.bind((self.server_ip, 0)) 

        self.ANSWER_RECEIVED = False
        self.ELECTION_IN_PROGRESS = False

        self.coordinator_message = f"COORDINATOR:{self.server_ip}:{self.server_tcp_port}"
        self.elect_message = f"ELECT:{self.server_ip}:{self.server_tcp_port}"

        self.messages_received_from_leader = {}
        self.leader_messages_counter = 0

        # Format the directory name
        self.dir_name = f"DBs/DB_{self.server_tcp_port}"        #if exists, delete it
        if os.path.exists(self.dir_name):
            os.rmdir(self.dir_name)
        os.makedirs(self.dir_name)

    def multicast_message(self, message):
        # message OPERTAION_LEADER_<OP>:operation:port:file_path
        message = f"{message}:{self.leader_messages_counter-1}"
        # Broadcast the message to all servers
        self.broadcast_socket.sendto(f'{message}'.encode(), ('<broadcast>', Server.SERVER_UDP_PORT))

    def discover_hosts(self):
        print("Discovering hosts...")
        self.broadcast_socket.sendto(f'DISCOVER:{self.server_tcp_port}'.encode(), ('<broadcast>', Server.SERVER_UDP_PORT))

    def listen_for_TCP(self):
        listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listen_socket.bind((self.server_ip, self.server_tcp_port))
        listen_socket.listen(5)

        while True:
            client_socket, addr = listen_socket.accept()
            message = client_socket.recv(1024).decode()
            # print(f"Received message: {message.strip()}")
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
            elif message.startswith('first update'):
                print("Received First Step of UPDATE")
                threading.Thread(target=self.handel_read_file, args=(addr, message)).start()
                #give token to client
            elif message.startswith('second update'):
                print("Received Second Step of UPDATE")
                threading.Thread(target=self.handel_write_file, args=(addr, message, client_socket)).start()
                #take token from client
            elif message.startswith('delete'):
                print("Received DELETE")
                threading.Thread(target=self.handel_delete_file, args=(addr, message)).start()
                continue
            elif message.startswith('DB'):
                print("Received DB")
                threading.Thread(target=self.getDB, args=(client_socket,)).start()
                continue
            elif message.startswith('OK'):
                threading.Thread(target=self.handel_ok, args=(addr, message)).start()
            elif message.startswith('COORDINATOR'):
                _, ip, port = message.split(':')
                #if I deserve to be leader more than the sender, I start an election
                if f"{ip}:{port}" < f"{self.server_ip}:{str(self.server_tcp_port)}":
                    print("Starting election because I deserve to be leader more than the COORDINATOR sender")
                    self.ELECTION_IN_PROGRESS = True
                    threading.Thread(target=self.start_bully).start()
                else:
                    self.handel_coordinator(addr, message)
                # threading.Thread(target=self.handel_coordinator, args=(addr, message)).start()
            elif message.startswith('ELECT'):
                # self.handel_elect(addr, message)
                _, ip, port = message.split(':')
                if f"{ip}:{port}" >= f"{self.server_ip}:{self.server_tcp_port}":
                    print("Ignoring ELECT from " + str(port) + " and I am " + str(self.server_tcp_port))
                    continue
                threading.Thread(target=self.handel_elect, args=(addr, message)).start()
            elif message.startswith('ANSWER'):
                self.ANSWER_RECEIVED = True
                
    def handel_coordinator(self, addr, message):
        _, ip, port = message.split(':')
        self.leader = f"{ip}:{port}"
        self.is_leader = False
        self.ELECTION_IN_PROGRESS = False
        print("Am I Leader from bully: " + str(self.is_leader))

    def handel_elect(self, addr, message):
        _, ip, port = message.split(':')

        #send tcp ok message to sender
        send_tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        send_tcp_socket.bind((self.server_ip, 0))
        try:
            send_tcp_socket.connect(((ip, int(port))))
            send_tcp_socket.send(f'ANSWER:{self.server_tcp_port}'.encode())
        except socket.error as e:
            # print("fe hannnnddeellelll ellelldllcllrt")
            print("Could not connect to server: ", server)
        if not self.ELECTION_IN_PROGRESS:
            print("Habda2 election 3ashan 7ad ba3atly elect" + str(port))
            self.ELECTION_IN_PROGRESS = True
            threading.Thread(target=self.start_bully).start()
            # self.start_bully()
       
    def listen_for_UDP(self):
        print("Listening for UDP Messages...")
        listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listen_socket.bind(('0.0.0.0', Server.SERVER_UDP_PORT))

        while True:
            message, addr = listen_socket.recvfrom(4096)
            #print(f"Received response from {addr}")
            decoded_message = message.decode()
            if decoded_message.startswith('DISCOVER'):
                threading.Thread(target=self.handel_discover, args=(addr, decoded_message)).start()
            elif decoded_message.startswith('WHO_IS_THE_LEADER'):
                threading.Thread(target=self.handel_who_is_leader, args=(addr, decoded_message)).start()
            elif decoded_message.startswith('OPERATION_LEADER_DELETE'):
                if not self.is_leader:
                    threading.Thread(target=self.handel_delete_file_non_leader, args=(addr, decoded_message)).start()
            elif decoded_message.startswith('OPERATION_LEADER_WRITE'):
                if not self.is_leader:
                    threading.Thread(target=self.handel_write_file_non_leader, args=(addr, decoded_message)).start()
            elif decoded_message.startswith('HEARTBEAT'):
                threading.Thread(target=self.handel_heartbeat, args=(addr, decoded_message)).start()
            # elif decoded_message.startswith('GET_TREE'):
            #     threading.Thread(target=self.handel_get_tree, args=(addr, decoded_message)).start()
            # else:
            #     print(f"Received from Leader: {decoded_message}")
    
    def getDB(self, conn):
        '''Receive DB with all files from leader'''

        def receive_file(conn, filename):
            with open(self.dir_name + '/' + filename, 'wb') as file:
                while True:
                    file_data = conn.recv(1024)
                    if file_data.endswith(b"\nEOF\n"):
                        file.write(file_data[:-5])  # Write data excluding the EOF marker
                        break
                    file.write(file_data)
        while True:
            header = conn.recv(1024)
            if not header:
                break
            filename = header.decode().strip()
            if filename == "EOF":
                break  # End of file transfer
            receive_file(conn, filename)

    def handel_discover(self, addr, message):
        # ... [existing Server class definition] ...

        def send_all_files(server_ip, server_port):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((server_ip, server_port))
                # Send a signal to indicate the start of file transfer
                print("Sending DB to new server...")
                print("new server port: ", str(server_port))
                s.sendall(b"DB")
                # Now send the files
                for filename in os.listdir(self.dir_name):
                    filepath = os.path.join(self.dir_name, filename)
                    if os.path.isfile(filepath):
                        # Send file name
                        s.sendall(filename.encode() + b"\n")
                        # Send file data
                        with open(filepath, 'rb') as file:
                            file_data = file.read()
                            s.sendall(file_data + b"\nEOF\n")
                # Signal the end of the transfer
                s.sendall(b"EOF\n")
                print("All files sent.")


        _, port = message.split(':')

        server_config = {'ip': addr[0], 'port': int(port)}

        if server_config != {'ip': self.server_ip, 'port': self.server_tcp_port}:
            if server_config not in self.servers:
                if self.is_leader:
                    print("Sending DB to new server...")
                    print("new server port: ", str(port))
                    send_all_files(addr[0], int(port))
                print(f"$$Adding server: {server_config} to discovered servers")
                self.servers.append(server_config)

                # self.start_bully()
            
            # send_ack_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # # get available port
            # send_ack_socket.bind((self.server_ip, 0))
            # # should send server ip not port
            # send_ack_socket.sendto(f'OK:{self.server_tcp_port}'.encode(), (addr[0], Server.SERVER_UDP_PORT))
            send_tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            send_tcp_socket.bind((self.server_ip, 0))
            send_tcp_socket.connect(((addr[0], int(port))))
            send_tcp_socket.send(f'OK:{self.server_tcp_port}'.encode())
            send_tcp_socket.close()
            
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
                print(f"**Adding server: {server_config} to discovered servers")
                self.servers.append(server_config)
                # print(self.servers)

                # self.elect_leader()

    def handel_heartbeat(self, addr, message):
        _, port = message.split(':')
        # print("Received HEARTBEAT")
        self.last_heartbeat[f"{addr[0]}:{port}"] = time.time()

    def handel_get_tree(self, addr, message):
        r"""Sends the directory tree to the client"""

        _, port = message.split(':')
        if self.is_leader:
            tree = utils.build_directory_tree(self.dir_name)
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

    def handel_delete_file_non_leader(self, addr, message):
        r"""Deletes the file from the server"""

        # OPERATION_LEADER_DELETE:operation:port:file_path:counter
        _, operation, port, file_path, counter = message.split(':')
        port = int(port)
        
        self.messages_received_from_leader[f"{counter}"] = f"{operation}:{port}:{file_path}"
        self.leader_messages_counter = counter

        relative_path = self.dir_name + file_path
        #delete the file in DB/file_path; handle deletion on all OSs
        if os.path.exists(relative_path):
            os.remove(relative_path)
            print(f"File {relative_path} has been deleted.")
        else:
            print(f"The file {relative_path} does not exist.")

    def handel_delete_file(self, addr, message):
        r"""Deletes the file from the server"""

        operation, port, file_path = message.split(':')
        port = int(port)

        relative_path = self.dir_name + file_path
        #delete the file in DB/file_path; handle deletion on all OSs
        if os.path.exists(relative_path):
            os.remove(relative_path)
            print(f"File {relative_path} has been deleted.")
        else:
            print(f"The file {relative_path} does not exist.")
        
        self.messages_received_from_leader[f"{self.leader_messages_counter}"] = message
        self.leader_messages_counter += 1

        # multicast to other servers to delete the file
        self.multicast_message(f"OPERATION_LEADER_DELETE:{message}")
        
        # send <DONE> to client
        send_done_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        send_done_socket.connect((addr[0], int(port)))
        send_done_socket.send("<DONE>".encode())
        send_done_socket.close()        

    def handel_write_file_non_leader(self, addr, message):
        r"""
        Receive the file from the leader and save it in the server
        """
        # OPERATION_LEADER_WRITE:operation:port:file_path:content:counter
        _, operation, port, file_path, file_content, counter = message.split(':')
        file_path = file_path.strip()
        port = int(port)

        if self.messages_received_from_leader+1 == counter:
            self.messages_received_from_leader[f"{counter}"] = f"{operation}:{port}:{file_path}"
            self.leader_messages_counter = counter

            with open(self.dir_name + '/' + file_path, 'w') as f:
                f.write(file_content)
        elif self.messages_received_from_leader+1 > counter:
            print("Duplicate message received")
            pass
        else:
            print("Message is messing")
            pass

    def handel_write_file(self, addr, message, client_socket):
        r"""
        Receive the file from the client and save it in the server
        """

        operation, port, file_path = message.split(':')
        file_path = file_path.strip()
        port = int(port)

        file_content = utils.receive_file(file_path, client_socket, self.dir_name)
        self.messages_received_from_leader[f"{self.leader_messages_counter}"] = f"{message}:{file_content}"
        self.leader_messages_counter += 1

        # multicast to other servers to update the file
        self.multicast_message(f"OPERATION_LEADER_WRITE:{message}:{file_content}")
        
        # send <DONE> to client
        send_done_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        send_done_socket.connect((addr[0], int(port)))
        send_done_socket.send("<DONE>".encode())
        send_done_socket.close()

    def send_heartbeat(self):
        while True:
            self.HEARTBEAT_SOCKET.sendto(f"HEARTBEAT:{self.server_tcp_port}".encode(), ('<broadcast>', Server.SERVER_UDP_PORT))
            time.sleep(Server.HEARTBEAT_INTERVAL)

    def check_last_heartbeat(self):
        while True:
            dead_servers = []
            for addr, last_time in list(self.last_heartbeat.items()):
                if time.time() - last_time > Server.TIMEOUT:
                    # print(f"Server {addr} has died")
                    # print("Leader:" + str(self.leader))
                    ip, port = addr.split(':')
                    dead_server = {'ip': ip, 'port': int(port)}
                    self.servers.remove(dead_server)
                    dead_servers.append(dead_server)
                    del self.last_heartbeat[addr]
            for server in dead_servers:
                if self.leader == f"{server['ip']}:{server['port']}":
                            if not self.ELECTION_IN_PROGRESS:
                                # print("Leader is dead")
                                self.leader = None
                                self.is_leader = False
                                self.ELECTION_IN_PROGRESS = True
                                print("Habda2 election 3ashan ektashaft el leader maat")
                                # self.start_bully()
                                threading.Thread(target=self.start_bully).start()
            # print("Current servers: ", self.servers)
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

        # self.elect_leader()
        threading.Thread(target=self.start_bully).start()
        # self.start_bully()
        # time.sleep(2)
        #threading.Thread(target=self.heartbeat).start()
        threading.Thread(target=self.send_heartbeat, daemon=True).start()
        threading.Thread(target=self.check_last_heartbeat, daemon=True).start()
        print("Server Started...")
    
    def start_bully(self):

        def send_message_to_servers(servers, message):
            # print('sending message to servers' + str(message))
            # print("servers: " + str(servers))
            print("Me" + str(self.server_tcp_port))
            print("Sending message to all servers")
            for server in servers:
                #print the port
                print("server port: " + str(server['port']))
            for server in servers:
                if server == {'ip': self.server_ip, 'port': self.server_tcp_port}:
                    continue
                if int(server['port']) == self.server_tcp_port:
                    continue
                send_tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    send_tcp_socket.bind((self.server_ip, 0))
                    send_tcp_socket.connect(((server['ip'], int(server['port']))))
                    send_tcp_socket.send(message.encode())
                    print("I am server " + str(self.server_tcp_port) + " and I sent " + str(message.split(':')[0]) + " to " + str(server['port']))
                    print(server['port'] == str(self.server_tcp_port))
                    send_tcp_socket.close()
                except socket.error as e:
                    print("Could not connect to server: ", server)

        # self.previous_leadership = self.is_leader
        # self.is_leader = True
        print('Starting Bully')
        self.ELECTION_IN_PROGRESS = True
        larger_servers = []
        for server in self.servers:
            if f"{server['ip']}:{server['port']}" > f"{self.server_ip}:{self.server_tcp_port}":
                print("ME: " + str(self.server_tcp_port)+ "am smaller than " + str(server['port']))
                self.is_leader = False
                larger_servers.append(server)

        #BASE CASE       
        if len(larger_servers) == 0:
            #send coordinator message to all servers
            send_message_to_servers(self.servers, self.coordinator_message)
            self.is_leader = True
            self.leader = f"{self.server_ip}:{self.server_tcp_port}"
            self.ELECTION_IN_PROGRESS = False
            print(f"Am I Leader from bully: {self.is_leader}")
        else:
            while True:
                # print('Starting Bully Loop')
                # print("Me: " + str(self.server_ip) + ":" + str(self.server_tcp_port))
                # print("Larger Servers: " + str(larger_servers))
                #phase 1
                self.ANSWER_RECEIVED = False
                #send elect to every larger server
                send_message_to_servers(larger_servers, self.elect_message)
                time.sleep(Server.T_Phase1)
                # print('Before Answer Received')
                #phase 2
                if self.ANSWER_RECEIVED:
                    # print("ANSWER RECEIVED")
                    time.sleep(Server.T_Phase2)
                    # print('After T_Phase2')
                    if not self.ELECTION_IN_PROGRESS:
                        break
                else:
                    # print("ANSWER NOT RECEIVED")
                    #send coordinator message to all servers
                    send_message_to_servers(self.servers, self.coordinator_message)
                    self.is_leader = True
                    self.leader = f"{self.server_ip}:{self.server_tcp_port}"
                    self.ELECTION_IN_PROGRESS = False
                    print(f"Am I Leader from bully: {self.is_leader}")
                    break
       
   
if __name__ == '__main__':
    server = Server()
    server.start()
    voltage = 0
    while True:
        pass