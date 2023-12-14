import socket
import time
import threading


class Client:
    SERVER_UDP_PORT = 5000
    def __init__(self):
        self.leader = None
        self.client_port = self.get_available_port()
        threading.Thread(target=self.listen_for_ack).start()

    def discover_leader(self):
        r"""Broadcasts a message to all servers to discover the leader"""
        discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        discovery_socket.sendto(f'WHO_IS_THE_LEADER:{self.client_port}'.encode(), ('255.255.255.255', Client.SERVER_UDP_PORT))
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

    def send_message(self, message):
        r"""Sends a message to the leader server"""
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

                except Exception as e:
                    print(f"An error occurred: {e}")

                break
            time.sleep(1)

    def get_available_port(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            port = s.getsockname()[1]
        return port
    
if __name__ == '__main__':
    
    client = Client()
    while True:
        message = input("Enter message: ")
        client.send_message(message)
        #threading.Thread(target=client.send_message, args=(message,)).start()    