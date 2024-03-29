import os
import pickle

def send_file(file_path, client, server_tcp_port):
    try:
        file = open(f'DBs/DB_{server_tcp_port}'+file_path, 'rb')
        data = file.read(1024)

        while data:
            client.send(data)
            data = file.read(1024)
        client.send('<End>'.encode())
        file.close()
        return True
    except ConnectionResetError: #If the client disconnected
        return False


def receive_file(filename, client_socket, dir_name):
    try:
        data = client_socket.recv(1024).decode()
        print('RECEIVED DATA: '+data)
        print('filename: '+filename)
        
        with open(dir_name + '/' +filename, 'w') as f: 
            file_content = ""
            while True:
                if data.endswith('<End>'):
                    data = data[:-5]
                    file_content += data
                    break
                else:
                    file_content += data
                data = client_socket.recv(1024).decode()
            f.write(file_content)
        
        return file_content

    except ConnectionResetError:#If the client disconnected
        print('CLIENT DISCONNECTED')
  

def build_directory_tree(directory):
    # create directory if it doesn't exist
    if not os.path.exists(directory):
        os.makedirs(directory)
    result = {}
    for item in os.listdir(directory):
        item_path = os.path.join(directory, item)
        if os.path.isdir(item_path):
            result[item] = build_directory_tree(item_path)
        else:
            result[item] = None  # You can set it to a specific value or leave it as None
    return result


def send_tree_to_client(client):
    tree = build_directory_tree('sender_folder/')
    tree = pickle.dumps(tree)
    client.sendall(tree)
    

def server_main_app(client):
        print('==============================================')
        print('CONNECTED TO A CLIENT...')

        try: 
            # Send the tree of directories and files on the server
            send_tree_to_client(client)
        except ConnectionResetError:#If the client disconnected:
            print('CLIENT DISCONNECTED')
            connection_opened = False
            client.close()
            return

        connection_opened = True
        #SERVE THIS CLIENT WITH AS MANY OPERATIONS AS HE WANTS
        while connection_opened:
            try:
                operation_path = client.recv(1024).decode() #Receive the operation and filename from the client
            except ConnectionResetError:#If the client disconnected:
                print('CLIENT DISCONNECTED')
                connection_opened = False
                client.close()
                break
            print(operation_path)
            operation_path_list = operation_path.split(' ', 1)
            
            try:
                operation = operation_path_list[0].lower()
                #substring path to remove first 5 characters "root/"
                path = operation_path_list[1][5:]
                print(path)
            except:
                #Close the connection because the client request errors are handled at client. 
                #If the client sent an invalid request, then it means that the client is not working properly
                print('CLIENT REQUESTED INVALID OPERATION')
                connection_opened = False
                client.close()
                break
            
            print('CLIENT REQUESTED OPERATION: '+operation_path)
            match operation:
                case 'download':
                    success = send_file(path, client)
                    if not success:
                        print('CLIENT DISCONNECTED')
                        connection_opened = False
                        client.close()
                        break
                    print('DOWNLOAD REQUEST SERVED!')
                case 'upload':
                    print('RECEIVING FILE...')
                    success = receive_file(path, client)
                    if not success:
                        print('CLIENT DISCONNECTED')
                        connection_opened = False
                        client.close()
                        break
                    print('UPLOAD REQUEST SERVED!')
                case 'update':
                    print('SENDING CURRENT FILE STATUS...')
                    success = send_file(path, client)
                    if not success:
                        print('CLIENT DISCONNECTED')
                        connection_opened = False
                        client.close()
                        break
                    print('FILE STATUS SENT!')
                    print('RECEIVING UPDATED FILE...')
                    success = receive_file(path, client)
                    if not success:
                        print('CLIENT DISCONNECTED')
                        connection_opened = False
                        client.close()
                        break
                    print('UPDATE REQUEST SERVED!')
                case 'delete':
                    try:
                        os.remove('sender_folder/'+path)
                    except ConnectionResetError:
                        send_tree_to_client(client)
                        client.send(b'<Fail>')
                    send_tree_to_client(client)
                    client.send(b'<Done>')
                    print('DELETE REQUEST SERVED!')
                case 'create':
                    pass
                case 'cd':
                    pass

            try:
                if(client.recv(1024).decode() == '<Exit>'):
                    connection_opened = False
                    client.close()
            except ConnectionResetError:
                print('CLIENT DISCONNECTED')
                connection_opened = False
                client.close()
                break
        print('CLIENT OPERATION TERMINATED...')


def stringfyServers(x):
    return f"{x['ip']}:{x['port']}"

