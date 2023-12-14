import socket
import time
import threading
import sys
from utils.utils_client import *

class Client:
    SERVER_UDP_PORT = 5000
    def __init__(self):
        self.leader = None
        self.client_port = self.get_available_port()
        self.current_directory = 'root'
        self.directories_dict = {}
        threading.Thread(target=self.listen_for_UDP, daemon=True).start()

    def discover_leader(self):
        r"""Broadcasts a message to all servers to discover the leader"""
        discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        discovery_socket.sendto(f'WHO_IS_THE_LEADER:{self.client_port}'.encode(), ('255.255.255.255', Client.SERVER_UDP_PORT))
        discovery_socket.close()
    
    def listen_for_UDP(self):
        r"""Listens for a response from the leader server"""

        listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        listen_socket.bind(('', self.client_port))

        while True:
            message, addr = listen_socket.recvfrom(1024)
            #print(f"Received response {message.decode()}")
            # print(message)
            if message.decode().startswith('I_AM_THE_LEADER:'):
                self.server_port = int(message.decode().split(':')[1])
                self.leader = addr
            elif message.decode().startswith('TREE'):
                _, tree = message.decode().split(':', 1)
                import json
                self.directories_dict = json.loads(tree)

        listen_socket.close()

    def get_tree(self):
        r"""Broadcasts a message to all servers to discover the leader"""
        get_tree_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        get_tree_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        get_tree_socket.sendto(f'GET_TREE:{self.client_port}'.encode(), ('255.255.255.255', Client.SERVER_UDP_PORT))
        get_tree_socket.close()

    def prepare_operation(self):
        r"""Prepares the operation to be sent to the leader server"""

        directories_dict = self.directories_dict
        while True: #loop until valid input
            # directories_dict = receive_tree_from_server(client)
            try:
                # Print the files on the server and the operations that can be done
                self.get_tree()
                prompt_user(directories_dict, self.current_directory)
                operation_filename = input('Please enter your operation: \n')
                operation_filename_list = operation_filename.split(' ', 1)
                operation = operation_filename_list[0].lower()
                if operation == 'exit': 
                    filename = None
                    break
                filename = operation_filename_list[1]
                if operation not in ['read', 'write', 'update', 'delete','cd']:
                    raise Exception
                if operation in ['read','update','delete'] and not is_valid_path(directories_dict, self.current_directory, filename):
                    print('This file does not exist, please enter a file from the list')
                    raise Exception
                if operation == 'write' and not os.path.exists(filename):#check that file exists on client side
                    raise Exception
                if operation == 'write' and is_valid_path(directories_dict, self.current_directory, filename): 
                    if input('File already exists on the server, do you want to overwrite it? (y/n) \n') != 'y':
                        continue #if user doesn't want to overwrite, re-prompt user for another operation
                if operation == 'delete' and input('Are you sure you want to delete this file? (y/n) \n') != 'y':
                    continue #if user doesn't want to delete, re-prompt user for another operation
                if operation == 'cd'and not is_valid_directory(directories_dict, self.current_directory, filename):
                        raise Exception
                break #break out of loop if valid input
            #handle if invalid input
            except:
                print('Invalid input, please try again')

        return operation, filename
            
    def initiate_operation(self):
        r"""Sends a message to the leader server"""

        while True:
            self.discover_leader()
            time.sleep(1)
            if self.leader is None:
                print("No leader found")
            else:
                break

        self.get_tree()
        time.sleep(1)
        # do the local operations

        operation, filename = self.prepare_operation()

        # check for exit
        if not operation == 'exit':
            # send operation to the leader
            print("dsbfdbsfdsbfdhsfdhgh")
            message = None
            while True:
                self.discover_leader()
                time.sleep(1)
                if self.leader is None:
                    print("No leader found")
                else:
                    try:
                        print(f"Sending message to the leader: {(self.leader[0], self.server_port)}")
                        with socket.create_connection((self.leader[0], self.server_port), timeout=1) as client_socket:
                            client_socket.send(message.encode())
                            self.leader = None
                        # client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        # client.connect((self.leader[0], self.server_port))
                        # client.send('I AM CLIENT'.encode())
                        # client_main_app(client)
                        #threading.Thread(target=client_main_app, args=(client,)).start()
                        break

                    except Exception as e:
                        print(f"An error occurred: {e}")
                    #break
                time.sleep(1)

    def get_available_port(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            port = s.getsockname()[1]
        return port
    
if __name__ == '__main__':
    
    client = Client()
    # while True:
        # message = input("Enter message: ")
    client.initiate_operation()
    print('==============================================')
        #threading.Thread(target=client.send_message, args=(message,)).start()    