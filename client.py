import socket
import time
import threading
import sys
import utils.utils_client as utils
import os
import json
import uuid


class Client:
    SERVER_UDP_PORT = 5000
    UPLOAD_TIMEOUT = 5
    def __init__(self):
        self.leader_ip = None
        self.client_port = self.get_available_port()
        self.client_ip = socket.gethostbyname(socket.gethostname())
        print(f"Client IP: {self.client_ip}")
        print(f"Client Port: {self.client_port}")
        self.current_directory = ''
        self.directories_dict = {}
        self.operation_done_flag = False
        threading.Thread(target=self.listen_for_TCP, daemon=True).start()

    def discover_leader(self):
        r"""Broadcasts a message to all servers to discover the leader"""
        discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        discovery_socket.bind((self.client_ip, 0))
        discovery_socket.sendto(f'WHO_IS_THE_LEADER:{self.client_port}'.encode(), ('255.255.255.255', Client.SERVER_UDP_PORT))
        discovery_socket.close()
    
    def listen_for_TCP(self):
        r"""Listens for a response from the leader server"""

        listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listen_socket.bind((self.client_ip, self.client_port))
        listen_socket.listen(5)

        while True:
            client_socket, addr = listen_socket.accept()
            message = client_socket.recv(1024).decode()

            if message.startswith('I_AM_THE_LEADER:'):
                self.server_port = int(message.split(':')[1])
                self.leader_ip = addr[0]
            elif message.startswith('TREE'):
                _, tree = message.split(':', 1)
                self.directories_dict = json.loads(tree)
            elif message.startswith('FILE'):
                filename = message.split(':')[1]
                utils.read_file_from_server(filename, client_socket)
            elif message.startswith('<DONE>'):
                self.operation_done_flag = True

    def get_tree(self):
        r"""Broadcasts a message to all servers to discover the leader"""
        self.send_TCP_message(f'GET_TREE:{self.client_port}')

    def prepare_operation(self):
        r"""Prepares the operation to be sent to the leader server"""

        directories_dict = self.directories_dict
        while True: #loop until valid input
            # directories_dict = receive_tree_from_server(client)
            try:
                # Print the files on the server and the operations that can be done
                self.get_tree()
                utils.prompt_user(directories_dict, self.current_directory)
                operation_filename = input('Please enter your operation: \n')
                operation_filename_list = operation_filename.split(' ', 1)
                operation = operation_filename_list[0].lower()
                if operation == 'exit': 
                    filename = None
                    break
                filename = operation_filename_list[1]
                if operation not in ['read', 'write', 'update', 'delete','cd']:
                    raise Exception
                if operation in ['read','update','delete'] and not utils.is_valid_path(directories_dict, self.current_directory, filename):
                    print('This file does not exist, please enter a file from the list')
                    raise Exception
                if operation == 'write' and not os.path.exists(f"locals/{filename}"):#check that file exists on client side
                    raise Exception
                if operation == 'write' and utils.is_valid_path(directories_dict, self.current_directory, filename): 
                    if input('File already exists on the server, do you want to overwrite it? (y/n) \n') != 'y':
                        continue #if user doesn't want to overwrite, re-prompt user for another operation
                if operation == 'delete' and input('Are you sure you want to delete this file? (y/n) \n') != 'y':
                    continue #if user doesn't want to delete, re-prompt user for another operation
                if operation == 'cd'and not utils.is_valid_directory(directories_dict, self.current_directory, filename):
                        raise Exception
                break #break out of loop if valid input
            #handle if invalid input
            except:
                print('Invalid input, please try again')

        return operation, filename

    def send_TCP_message(self, message):
        if self.leader_ip is not None:
            send_tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            send_tcp_socket.bind((self.client_ip, 0))
            send_tcp_socket.connect(((self.leader_ip, self.server_port)))
            send_tcp_socket.send(message.encode())
            send_tcp_socket.close()

    def upload_file(self, operation, file_path, local_folder='locals'):
        # Generate a random UUID
        while True:
            self.operation_done_flag = False
            operation_path = f"{operation}:{self.client_port}:{self.current_directory}/{file_path}"
            header = f"{operation_path:<1024}" # 1024 is the size of the header

            send_file_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            send_file_socket.bind((self.client_ip, 0))
            send_file_socket.connect(((self.leader_ip, self.server_port)))
            send_file_socket.send(header.encode())

            try:
                filename = file_path.split('/')[-1]
                with open(f"{local_folder}/{filename}", 'rb') as file:
                    data = file.read(1024)
                    while data:
                        send_file_socket.send(data)
                        data = file.read(1024)
                    send_file_socket.send(b'<End>')

                now = time.time()
                end = now
                while end - now < Client.UPLOAD_TIMEOUT:
                    if self.operation_done_flag:
                        break
                    end = time.time()

                if not self.operation_done_flag:
                    print('Could not write to the server')
                    print('Trying again...')
                    # we can set a counter here to try a certain number of times
                    continue

                self.get_tree()
                print('The file was successfully written to the server')
                break

            except Exception as e:
                print(f"An error occurred: {e}")
                print('Trying again...')
                # we can set a counter here to try a certain number of times
                continue

        print("These are the files currently in the server after writing")
        utils.print_directory_tree(self.directories_dict)

    def initiate_operation(self):
        r"""Sends a message to the leader server"""
        do_another_operation = True
        while do_another_operation:
            # if there is no leader, discover one
            # if there is a leader, get the tree then set the leader to None
            while True:
                self.discover_leader()
                time.sleep(1)
                if self.leader_ip is None:
                    print("No leader found")
                else:
                    self.get_tree()
                    self.leader_ip = None
                    break

            # do the local operations
            operation, filename = self.prepare_operation()

            # check for exit
            if operation == 'exit':
                sys.exit()
            # send operation to the leader
            while True:
                self.discover_leader()
                time.sleep(1)

                if self.leader_ip is None:
                    print("No leader found")
                else:
                    #try:
                    match operation:
                        case 'read':
                            operation_path = f"{operation}:{self.client_port}:{self.current_directory}/{filename}"
                            self.send_TCP_message(operation_path)
                            self.leader_ip = None

                            if input('Do you want to do more operations? (y/n) \n') != 'y':
                                do_another_operation = False
                            break
                        case 'write':
                            self.upload_file(operation, filename)

                            if input('Do you want to do more operations? (y/n) \n') != 'y':
                                do_another_operation = False
                            break

                        case 'update':         
                            operation_path = operation + ' ' + current_directory + '/' + filename       
                            client.send(operation_path.encode())
                            print('The file will now be opened automatically, please make your changes and save the file')
                            utils.read_file_from_server(operation_path, client)
                            while True:
                                user_done = input('Once you are done, please close the file and enter "y" \n') == 'y'
                                if user_done:
                                    utils.write_file_to_server(filename, client)
                                    directories_dict = utils.receive_tree_from_server(client)        
                                    print(client.recv(1024).decode())#print the server response
                                    break
                                else: 
                                    if input('Are you sure you want to exit without updating the file on the server? (y/n) \n') == 'y':
                                        client.send(b'<Cancel>')#inform server that update was cancelled
                                        break
                            
                            if input('Do you want to do more operations? (y/n) \n') != 'y':
                                # client.send(b'<Continue>')#inform server that I want to do more operations
                                do_another_operation = False
                            break
                        case 'delete':
                            # if check_filename_exists(filename, filenames_in_directory) == False:
                            #     continue
                            operation_path = operation + ' ' + current_directory + '/' + filename
                            client.send(operation_path.encode())
                            directories_dict = utils.receive_tree_from_server(client)
                            print("These are the files currently in the server "  + str(directories_dict) + " directory: ")
                            print(client.recv(1024).decode())#print the server response <Done>   
                                            
                            if input('Do you want to do more operations? (y/n) \n') != 'y':
                                # client.send(b'<Continue>')#inform server that I want to do more operations
                                do_another_operation = False
                            break
                        case 'cd':
                            #get rid of back steps
                            current_directory, filename = utils.cd_back_steps(current_directory, filename)
                            #if there is a path after stepbacks, add it to the current directory
                            if filename != '':
                                current_directory += '/' + filename
                            continue
                        case _:#handle if invalid operation
                            print('Invalid input, please try again2')
                            continue
            
                    # except Exception as e:
                    #     print(f"An error occurred: {e}")

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