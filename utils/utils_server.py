import os
import pickle

def send_file(file_path, client):
    try:
        file = open('DB/'+file_path, 'rb')
        data = file.read(1024)

        while data:
            client.send(data)
            data = file.read(1024)
        client.send('<End>'.encode())
        file.close()
        return True
    except ConnectionResetError:#If the client disconnected
        return False


def receive_file(filename, client_socket, dir_name):
    try:
        data = client_socket.recv(1024).decode()
        # if data.endswith('<Cancel>'): # If the client cancelled the update operation
        #     return True # Return True because client cancelled the operation but didn't disconnect
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
    
# print('SERVER INITIALIZING...')
# server = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # TCP
# server.bind(('localhost', 9999))
# server.listen()
# print('SERVER RUNNING...')

def server_main_app(client):
        print('==============================================')
        print('CONNECTED TO A CLIENT...')
        # client, address = server.accept()
        # print(f'CLIENT {address} CONNECTED...')

        # connection_opened = True

        try: #First, send the tree of the directory and subdirectories to the client
            #Send the tree of directories and files on the server
            send_tree_to_client(client)
        except ConnectionResetError:#If the client disconnected:
            print('CLIENT DISCONNECTED')
            connection_opened = False
            client.close()
            return

        subfolder = ''
        connection_opened = True
        #SERVE THIS CLIENT WITH AS MANY OPERATIONS AS HE WANTS
        while connection_opened:
            
            
            try:
                # #Send the list of files on the server
                # client.send(str(files_on_server).encode())
                # #send the list of subfolders on the server
                # all_subdirectories = [x[0] for x in os.walk('sender_folder/'+subfolder)]
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
                case 'read':
                    success = send_file(path, client)
                    if not success:
                        print('CLIENT DISCONNECTED')
                        connection_opened = False
                        client.close()
                        break
                    print('READ REQUEST SERVED!')
                case 'write':
                    print('RECEIVING FILE...')
                    success = receive_file(path, client)
                    if not success:
                        print('CLIENT DISCONNECTED')
                        connection_opened = False
                        client.close()
                        break
                    print('WRITE REQUEST SERVED!')
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


