import socket
import time
import threading
import sys
from client import client_main_app

class Client:
    server_port_list = [8887, 8888, 8889]
    def __init__(self, server_port, client_port=5555):
        self.server_port = server_port
        self.leader = None
        self.client_port = client_port
        threading.Thread(target=self.listen_for_ack).start()

    def discover_leader(self):
        r"""Broadcasts a message to all servers to discover the leader"""

        for port in Client.server_port_list:
            discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            discovery_socket.sendto(f'WHO_IS_THE_LEADER:{self.client_port}'.encode(), ('255.255.255.255', port))
            discovery_socket.close()
    
    def listen_for_ack(self):
        r"""Listens for a response from the leader server"""

        listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        listen_socket.bind(('', self.client_port))

        while True:
            message, addr = listen_socket.recvfrom(1024)
            #print(f"Received response {message.decode()}")
            if message.decode().startswith('I_AM_THE_LEADER:'):
                self.server_port = int(message.decode().split(':')[1])
                self.leader = addr
                #break

        listen_socket.close()

    def initiate_operation(self):
        r"""Sends a message to the leader server"""
        while True:
            self.discover_leader()
            time.sleep(1)
            if self.leader is None:
                print("No leader found")
            else:
                try:
                    print(f"Sending message to the leader: {(self.leader[0], self.server_port)}")
                    # with socket.create_connection((self.leader[0], self.server_port), timeout=1) as client_socket:
                    #     client_socket.send(message.encode())
                    #     self.leader = None
                    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client.connect((self.leader[0], self.server_port))
                    client.send('I AM CLIENT'.encode())
                    client_main_app(client)

                except Exception as e:
                    print(f"An error occurred: {e}")
                break
            time.sleep(1)
                    

if __name__ == '__main__':
    
    client = Client(int(sys.argv[1]), int(sys.argv[2]))
    # while True:
        # message = input("Enter message: ")
    client.initiate_operation()
        #threading.Thread(target=client.send_message, args=(message,)).start()    